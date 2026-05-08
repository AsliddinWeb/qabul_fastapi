"""Redis-backed OTP service.

Storage layout:
    Key: "otp:{purpose}:{phone}"
    Type: Redis hash {hash, attempts, created_at}
    TTL: settings.otp_ttl_seconds (default 120s)

    Cooldown key: "otp:cooldown:{purpose}:{phone}"
    Type: simple string "1"
    TTL: settings.otp_resend_cooldown_seconds (default 60s)

Security notes:
- Codes are stored hashed (SHA-256). Plain code never persists.
- Brute-force protection: `attempts` increments on every failed verify;
  exceeding `otp_max_attempts` invalidates the code.
- A confirmed verify deletes the entry — codes are single-use.
"""

from __future__ import annotations

import hashlib
import secrets

from redis.asyncio import Redis

from app.config import settings
from app.core.exceptions import AppError, UnauthorizedError, ValidationError
from app.core.logging import get_logger
from app.db.enums import OtpPurpose
from app.integrations.eskiz.client import EskizClient

logger = get_logger("otp")


def _key(purpose: OtpPurpose, phone: str) -> str:
    return f"otp:{purpose.value}:{phone}"


def _cooldown_key(purpose: OtpPurpose, phone: str) -> str:
    return f"otp:cooldown:{purpose.value}:{phone}"


def _hash_code(code: str) -> str:
    # Codes are short, but we still hash with the app secret to bind to install.
    salted = f"{settings.app_secret_key}:{code}".encode()
    return hashlib.sha256(salted).hexdigest()


def _generate_code(length: int) -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


class OtpRateLimitedError(AppError):
    status_code = 429
    code = "otp_rate_limited"
    message = "OTP requested too soon. Please wait before requesting again."


class OtpService:
    def __init__(self, redis: Redis, sms: EskizClient) -> None:
        self.redis = redis
        self.sms = sms

    async def issue(self, phone: str, purpose: OtpPurpose) -> tuple[int, int, bool]:
        """Generate + send OTP. Returns (ttl_seconds, cooldown_seconds, delivered).

        `delivered` is False only when SMS gateway is in dev-mode (no real send).

        Raises OtpRateLimitedError if a previous code is still within cooldown.
        Raises AppError("SMS delivery failed", ...) if the SMS gateway returns error.
        """
        cd_key = _cooldown_key(purpose, phone)
        if await self.redis.exists(cd_key):
            ttl = await self.redis.ttl(cd_key)
            raise OtpRateLimitedError(
                f"Iltimos, {ttl} soniya kuting va qaytadan urinib ko'ring"
            )

        code = _generate_code(settings.otp_length)
        code_hash = _hash_code(code)

        key = _key(purpose, phone)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.delete(key)
            pipe.hset(key, mapping={"hash": code_hash, "attempts": "0"})
            pipe.expire(key, settings.otp_ttl_seconds)
            pipe.set(cd_key, "1", ex=settings.otp_resend_cooldown_seconds)
            await pipe.execute()

        message = self._render_message(code, purpose)
        result = await self.sms.send_sms(phone, message)
        if not result.success:
            logger.error("otp.sms_failed", phone=phone, error=result.error)
            # Clean up so user can retry without waiting.
            await self.redis.delete(key, cd_key)
            # Translate underlying gateway error codes to user-friendly Uzbek
            err = result.error or ""
            if "login_failed" in err:
                msg = "SMS xizmatiga ulanib bo'lmadi. Administrator bilan bog'laning."
            elif "auth_invalidated" in err:
                msg = "SMS xizmati avtorizatsiyasi muddati o'tdi. Birozdan keyin urinib ko'ring."
            elif err.startswith("http_"):
                msg = "SMS xizmati javob bermayapti. Birozdan keyin urinib ko'ring."
            elif "timeout" in err.lower() or "ConnectError" in err:
                msg = "Internet aloqasi sekin yoki SMS xizmati ishlamayapti."
            else:
                msg = "SMS yuborib bo'lmadi. Telefon raqamingizni tekshiring va qayta urinib ko'ring."
            raise AppError(msg, code="sms_failed", status_code=502)

        # In dev-mode, sms.send_sms returns success=True with message_id="dev-mode"
        # but no real SMS is delivered. Surface that to caller.
        delivered = result.message_id != "dev-mode"

        logger.info(
            "otp.issued",
            phone=phone,
            purpose=purpose.value,
            ttl=settings.otp_ttl_seconds,
            message_id=result.message_id,
            delivered=delivered,
        )
        return settings.otp_ttl_seconds, settings.otp_resend_cooldown_seconds, delivered

    async def verify(self, phone: str, code: str, purpose: OtpPurpose) -> None:
        """Validate the code. Raises on any failure; deletes on success."""
        key = _key(purpose, phone)
        data = await self.redis.hgetall(key)
        if not data:
            raise UnauthorizedError("OTP code expired or not requested")

        attempts = int(data.get("attempts", "0"))
        if attempts >= settings.otp_max_attempts:
            await self.redis.delete(key)
            raise UnauthorizedError("Too many incorrect attempts. Request a new code.")

        if data.get("hash") != _hash_code(code):
            await self.redis.hincrby(key, "attempts", 1)
            raise UnauthorizedError("Invalid OTP code")

        # Success — single use.
        await self.redis.delete(key)
        logger.info("otp.verified", phone=phone, purpose=purpose.value)

    # ---------- helpers ----------
    @staticmethod
    def _render_message(code: str, purpose: OtpPurpose) -> str:
        # Eskiz requires every template to be pre-approved on their dashboard.
        # The text below MUST match the approved template exactly (the {code}
        # placeholder is the only varying part). Approved 2026-05-08:
        #   "Xalqaro innovatsion universiteti qabul tizimiga kirish kodingiz: 1234"
        return f"Xalqaro innovatsion universiteti qabul tizimiga kirish kodingiz: {code}"
