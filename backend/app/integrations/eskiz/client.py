"""Eskiz.uz SMS client — wraps the official `eskiz-pkg` async SDK.

The SDK handles auth + automatic token refresh internally; we keep a thin
wrapper to:
  • Preserve the existing `send_sms(phone, message) -> SmsResult` interface
    used by the OTP service.
  • Stay silent (dev-mode) when ESKIZ_EMAIL/ESKIZ_PASSWORD are empty so
    local/staging environments don't need real credentials.
  • Surface useful error codes back to callers (translated to user-friendly
    Uzbek messages by `OtpService.issue`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings
from app.core.logging import get_logger

logger = get_logger("eskiz")


@dataclass
class SmsResult:
    success: bool
    message_id: str | None = None
    raw: dict[str, Any] | None = None
    error: str | None = None


class EskizClient:
    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        sender: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.email = email or settings.eskiz_email
        self.password = password or settings.eskiz_password
        self.sender = sender or settings.eskiz_from
        self.timeout = timeout

    @property
    def is_configured(self) -> bool:
        return bool(self.email and self.password)

    async def send_sms(self, phone: str, message: str) -> SmsResult:
        # Eskiz expects digits only (no leading +).
        digits = phone.lstrip("+")
        try:
            phone_int = int(digits)
        except ValueError:
            return SmsResult(success=False, error="invalid_phone")

        if not self.is_configured:
            logger.warning(
                "eskiz.dev_mode",
                phone=digits,
                preview=message[:80],
                hint="Set ESKIZ_EMAIL and ESKIZ_PASSWORD to send real SMS.",
            )
            return SmsResult(success=True, message_id="dev-mode")

        # Import inside the method so missing optional dep doesn't crash app
        # startup in environments that don't send SMS.
        try:
            from eskiz.client import AsyncClient
        except ImportError as exc:
            logger.error("eskiz.sdk_missing", error=str(exc))
            return SmsResult(success=False, error="sdk_missing")

        try:
            async with AsyncClient(email=self.email, password=self.password) as client:
                resp = await client.send_sms(phone_number=phone_int, message=message)
        except Exception as exc:  # SDK raises a variety of exceptions
            err_text = str(exc).lower()
            if "login" in err_text or "auth" in err_text or "401" in err_text:
                code = "auth_invalidated"
            elif "timeout" in err_text or "connect" in err_text:
                code = "timeout"
            elif "400" in err_text or "forbidden" in err_text:
                code = "http_400"
            else:
                code = f"http_{type(exc).__name__.lower()}"
            logger.error("eskiz.send_failed", phone=digits, error=str(exc), code=code)
            return SmsResult(success=False, error=code)

        # SDK returns a pydantic model with .id, .message, .status fields.
        msg_id = getattr(resp, "id", None)
        status = getattr(resp, "status", None)
        raw = resp.model_dump() if hasattr(resp, "model_dump") else None

        if status in {"error", "failed"}:
            logger.warning("eskiz.bad_response", phone=digits, status=status, raw=raw)
            return SmsResult(success=False, error=f"status_{status}", raw=raw)

        return SmsResult(success=True, message_id=str(msg_id) if msg_id else None, raw=raw)


def get_eskiz_client() -> EskizClient:
    return EskizClient()
