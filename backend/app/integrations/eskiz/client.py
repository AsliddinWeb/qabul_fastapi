"""Eskiz.uz SMS client.

Authentication: POST /auth/login → JWT (valid ~30 days). The token is cached
in Redis to avoid re-login on every send.

In dev/staging without credentials, the client logs the message and returns
success — useful for local development without sending real SMS.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
from redis.asyncio import Redis

from app.config import settings
from app.core.logging import get_logger

logger = get_logger("eskiz")

_TOKEN_CACHE_KEY = "eskiz:token"
_TOKEN_CACHE_TTL_SECONDS = 25 * 24 * 3600  # 25 days (Eskiz tokens last ~30)


@dataclass
class SmsResult:
    success: bool
    message_id: str | None = None
    raw: dict[str, Any] | None = None
    error: str | None = None


class EskizClient:
    def __init__(
        self,
        redis: Redis | None = None,
        base_url: str | None = None,
        email: str | None = None,
        password: str | None = None,
        sender: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.redis = redis
        self.base_url = (base_url or settings.eskiz_base_url).rstrip("/")
        self.email = email or settings.eskiz_email
        self.password = password or settings.eskiz_password
        self.sender = sender or settings.eskiz_from
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.email and self.password)

    # ---------- token ----------
    async def _login(self, http: httpx.AsyncClient) -> str:
        resp = await http.post(
            f"{self.base_url}/auth/login",
            data={"email": self.email, "password": self.password},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        token = body.get("data", {}).get("token")
        if not token:
            raise RuntimeError(f"Eskiz login: no token in response: {body}")
        return token

    async def _get_token(self, http: httpx.AsyncClient) -> str:
        if self.redis is not None:
            cached = await self.redis.get(_TOKEN_CACHE_KEY)
            if cached:
                return cached

        token = await self._login(http)

        if self.redis is not None:
            await self.redis.set(_TOKEN_CACHE_KEY, token, ex=_TOKEN_CACHE_TTL_SECONDS)
        return token

    async def _invalidate_token(self) -> None:
        if self.redis is not None:
            await self.redis.delete(_TOKEN_CACHE_KEY)

    # ---------- public API ----------
    async def send_sms(self, phone: str, message: str) -> SmsResult:
        # Phone format Eskiz expects: 998XXXXXXXXX (no leading +).
        normalized = phone.lstrip("+")

        if not self.is_configured:
            logger.warning(
                "eskiz.dev_mode",
                phone=normalized,
                preview=message[:80],
                hint="Set ESKIZ_EMAIL and ESKIZ_PASSWORD to send real SMS.",
            )
            return SmsResult(success=True, message_id="dev-mode")

        async with httpx.AsyncClient(timeout=self.timeout) as http:
            try:
                token = await self._get_token(http)
            except (httpx.HTTPError, RuntimeError) as exc:
                logger.error("eskiz.login_failed", error=str(exc))
                return SmsResult(success=False, error=f"login_failed: {exc!s}")

            try:
                resp = await http.post(
                    f"{self.base_url}/message/sms/send",
                    headers={"Authorization": f"Bearer {token}"},
                    data={
                        "mobile_phone": normalized,
                        "message": message,
                        "from": self.sender,
                    },
                )
            except httpx.HTTPError as exc:
                logger.error("eskiz.http_error", error=str(exc))
                return SmsResult(success=False, error=str(exc))

            if resp.status_code == 401:
                # Token might be stale — invalidate cache and let next call re-login.
                await self._invalidate_token()
                logger.warning("eskiz.token_invalidated")
                return SmsResult(success=False, error="auth_invalidated")

            if resp.status_code >= 400:
                logger.warning(
                    "eskiz.bad_response",
                    status=resp.status_code,
                    body=resp.text[:300],
                )
                return SmsResult(success=False, error=f"http_{resp.status_code}", raw=_safe_json(resp))

            data = _safe_json(resp) or {}
            return SmsResult(
                success=True,
                message_id=str(data.get("id") or data.get("message_id") or ""),
                raw=data,
            )


def _safe_json(resp: httpx.Response) -> dict[str, Any] | None:
    try:
        return resp.json()
    except (ValueError, json.JSONDecodeError):
        return None
