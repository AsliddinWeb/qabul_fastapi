from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import ForbiddenError, TooManyRequestsError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
    verify_password,
)
from app.db.enums import OtpPurpose, UserRole
from app.integrations.eskiz.client import EskizClient
from app.modules.auth.otp import OtpService
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.schemas import (
    AuthSession,
    LoginResponse,
    OtpRequest,
    OtpRequestResponse,
    OtpVerify,
    RefreshRequest,
    StaffLogin,
    TokenPair,
)
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

logger = get_logger("auth")


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        redis: Redis,
        *,
        sms_client: EskizClient | None = None,
    ) -> None:
        self.session = session
        self.redis = redis
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.otp = OtpService(redis=redis, sms=sms_client or EskizClient())

    # ---------- OTP (applicant flow) ----------
    # ---- Abuse throttles (Redis; fail-open if Redis is down) ----
    _OTP_REQ_MAX_IP = 15          # OTP sends per IP per hour (anti SMS-bombing)
    _OTP_REQ_WINDOW = 3600
    _LOGIN_FAIL_MAX_PHONE = 10    # failed password logins per phone …
    _LOGIN_FAIL_MAX_IP = 30       # … and per IP, before a temporary block
    _LOGIN_FAIL_WINDOW = 900      # 15 min sliding block window

    async def request_otp(
        self, payload: OtpRequest, *, ip: str | None = None
    ) -> OtpRequestResponse:
        # Per-IP cap so one host can't bomb SMS to many numbers (each number is
        # separately protected by the per-phone resend cooldown in OtpService).
        if ip:
            try:
                k = f"auth:otp_ip:{ip}"
                n = await self.redis.incr(k)
                if n == 1:
                    await self.redis.expire(k, self._OTP_REQ_WINDOW)
                if n > self._OTP_REQ_MAX_IP:
                    raise TooManyRequestsError(
                        "Juda ko'p so'rov yuborildi. Bir ozdan so'ng urinib ko'ring."
                    )
            except TooManyRequestsError:
                raise
            except Exception:
                pass  # Redis down — degrade gracefully, don't block real users
        # We allow OTP for any phone — if user exists with non-applicant role,
        # verify_otp will reject. This avoids leaking which phones are staff.
        ttl, cooldown, delivered = await self.otp.issue(payload.phone, OtpPurpose.LOGIN)
        return OtpRequestResponse(
            phone=payload.phone, expires_in=ttl, resend_after=cooldown,
            delivered=delivered, code_length=settings.otp_length,
        )

    async def verify_otp(self, payload: OtpVerify) -> LoginResponse:
        await self.otp.verify(payload.phone, payload.code, OtpPurpose.LOGIN)

        user = await self.users.get_by_phone(payload.phone)
        if user and user.role != UserRole.APPLICANT:
            # Staff must use password login, not OTP.
            raise ForbiddenError(
                "This phone is registered as a staff account; use password login"
            )

        if user is None:
            user = await self.users.create(
                phone=payload.phone,
                role=UserRole.APPLICANT,
                is_active=True,
                is_phone_verified=True,
            )
        else:
            if not user.is_active:
                raise ForbiddenError("Account is deactivated")
            await self.users.update(
                user,
                is_phone_verified=True,
                last_login_at=datetime.now(timezone.utc),
            )

        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return LoginResponse(session=self._session_dto(user), tokens=tokens)

    # ---------- Staff (password) login ----------
    async def staff_login(
        self, payload: StaffLogin, *, ip: str | None = None
    ) -> LoginResponse:
        pkey = f"auth:login_fail:phone:{payload.phone}"
        ikey = f"auth:login_fail:ip:{ip}" if ip else None

        # Reject early if this phone or IP is already over the failure budget.
        if await self._login_blocked(pkey, ikey):
            raise TooManyRequestsError(
                "Juda ko'p urinish. 15 daqiqadan so'ng qayta urinib ko'ring."
            )

        user = await self.users.get_by_phone(payload.phone)
        # Same generic error for unknown phone and wrong password — no user
        # enumeration. Password mismatch and non-staff both count as a failure.
        credentials_ok = (
            user is not None
            and user.role != UserRole.APPLICANT
            and bool(user.password_hash)
            and verify_password(payload.password, user.password_hash)
        )
        if not credentials_ok:
            await self._register_login_failure(pkey, ikey)
            raise UnauthorizedError("Invalid phone or password")
        if not user.is_active:
            raise ForbiddenError("Account is deactivated")

        # Success — clear the failure counters for this phone.
        try:
            await self.redis.delete(pkey)
        except Exception:
            pass

        await self.users.update(user, last_login_at=datetime.now(timezone.utc))
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return LoginResponse(session=self._session_dto(user), tokens=tokens)

    async def _login_blocked(self, pkey: str, ikey: str | None) -> bool:
        try:
            pfails = int(await self.redis.get(pkey) or 0)
            ifails = int(await self.redis.get(ikey) or 0) if ikey else 0
        except Exception:
            return False  # Redis down — fail open, don't lock everyone out
        return pfails >= self._LOGIN_FAIL_MAX_PHONE or ifails >= self._LOGIN_FAIL_MAX_IP

    async def _register_login_failure(self, pkey: str, ikey: str | None) -> None:
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.incr(pkey)
                pipe.expire(pkey, self._LOGIN_FAIL_WINDOW)
                if ikey:
                    pipe.incr(ikey)
                    pipe.expire(ikey, self._LOGIN_FAIL_WINDOW)
                await pipe.execute()
        except Exception:
            pass

    # ---------- Refresh ----------
    # Grace window: a refresh token revoked within the last N seconds is
    # treated as a benign tab-race (some other tab JUST rotated tokens),
    # not a reuse attack. We fail this refresh call with 401 so the
    # frontend can pick up the fresh tokens via localStorage, but we do
    # NOT nuke every active session for the user. Without this every
    # multi-tab operator got logged out the moment two tabs hit a 401
    # at the same time.
    _REFRESH_REUSE_GRACE_SECONDS = 30

    async def refresh(self, payload: RefreshRequest) -> TokenPair:
        try:
            data = decode_token(payload.refresh_token)
        except ValueError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        if data.get("type") != "refresh":
            raise UnauthorizedError("Wrong token type")

        token_hash = hash_refresh_token(payload.refresh_token)
        record = await self.refresh_tokens.get_active_by_hash(token_hash)
        if not record:
            # Token isn't active right now. Two possibilities:
            #   1. Real reuse → someone is replaying a stolen refresh. Nuke.
            #   2. Tab-race → another tab just rotated; this token was
            #      revoked seconds ago. Reject this call but leave other
            #      sessions intact so the user keeps working.
            stale = await self.refresh_tokens.get_by_hash(token_hash)
            now = datetime.now(timezone.utc)
            within_grace = (
                stale is not None
                and stale.revoked_at is not None
                and (now - stale.revoked_at).total_seconds() <= self._REFRESH_REUSE_GRACE_SECONDS
            )
            if not within_grace:
                try:
                    user_id = UUID(str(data.get("sub")))
                    revoked = await self.refresh_tokens.revoke_all_for_user(user_id)
                    if revoked:
                        logger.warning("auth.refresh_reuse_suspected", user_id=str(user_id))
                        await self.session.commit()
                except ValueError:
                    pass
            else:
                logger.info(
                    "auth.refresh_tab_race_ignored",
                    user_id=str(data.get("sub")),
                    revoked_age_s=(now - stale.revoked_at).total_seconds() if stale and stale.revoked_at else None,
                )
            raise UnauthorizedError("Refresh token is no longer valid")

        user = await self.users.get(record.user_id)
        if not user or not user.is_active or user.deleted_at is not None:
            raise ForbiddenError("Account is no longer active")

        # Rotate: revoke old, issue new pair.
        await self.refresh_tokens.revoke(record)
        tokens = await self._issue_tokens(user)
        await self.session.commit()
        return tokens

    # ---------- Logout ----------
    async def logout(self, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        record = await self.refresh_tokens.get_by_hash(token_hash)
        if record and record.revoked_at is None:
            await self.refresh_tokens.revoke(record)
            await self.session.commit()
        # Silently succeed for unknown / already-revoked tokens.

    # ---------- helpers ----------
    async def _issue_tokens(self, user: User) -> TokenPair:
        extra = {"role": user.role.value, "phone": user.phone}
        access = create_access_token(str(user.id), extra=extra)
        refresh = create_refresh_token(str(user.id), extra=extra)

        expires_at = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_ttl_days)
        await self.refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh),
            expires_at=expires_at,
        )

        return TokenPair(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.jwt_access_ttl_min * 60,
        )

    @staticmethod
    def _session_dto(user: User) -> AuthSession:
        return AuthSession(
            user_id=str(user.id),
            phone=user.phone,
            role=user.role,
            is_phone_verified=user.is_phone_verified,
            is_consulting=user.is_consulting,
            is_root_superadmin=user.is_root_superadmin,
        )
