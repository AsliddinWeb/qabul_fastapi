"""Thin HTTP client for the external CRM.

Design rules:
  - CRM failures MUST NOT break the admission flow. Wrap calls in try/except,
    log failures, and rely on a background retry mechanism (Phase 12).
  - All calls are async (httpx).
  - Idempotency is provided by `external_id` in payloads — CRM dedupes.
  - This file is a STUB; real implementation comes in Phase 12.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.core.logging import get_logger
from app.integrations.crm.schemas import (
    ApplicantLead,
    ApplicantStatusUpdate,
    ContractCreatedEvent,
)

logger = get_logger("crm")


class CrmError(Exception):
    """Raised on CRM HTTP / protocol errors. Caller MUST decide whether to swallow."""


@dataclass
class CrmResult:
    success: bool
    status_code: int | None = None
    crm_id: str | None = None  # CRM-side identifier returned on creation
    raw: dict[str, Any] | None = None
    error: str | None = None


class CrmClient:
    """Stateless wrapper. One instance per request is fine; httpx pools internally."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or settings.crm_base_url).rstrip("/")
        self.api_key = api_key or settings.crm_api_key
        self.timeout = timeout
        self.enabled = bool(self.base_url and self.api_key)

    # ---------- internal ----------
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "xiu-admission/0.1",
        }

    async def _post(self, path: str, json: dict[str, Any]) -> CrmResult:
        if not self.enabled:
            logger.warning("crm.disabled", path=path)
            return CrmResult(success=False, error="crm_disabled")

        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http:
                resp = await http.post(url, headers=self._headers(), json=json)
        except httpx.HTTPError as exc:
            logger.error("crm.http_error", path=path, error=str(exc))
            return CrmResult(success=False, error=f"http_error: {exc!s}")

        if resp.status_code >= 400:
            logger.warning(
                "crm.bad_response",
                path=path,
                status=resp.status_code,
                body=resp.text[:500],
            )
            return CrmResult(
                success=False,
                status_code=resp.status_code,
                error=resp.text[:500],
            )

        try:
            data = resp.json()
        except ValueError:
            data = {}

        return CrmResult(
            success=True,
            status_code=resp.status_code,
            crm_id=str(data.get("id")) if data.get("id") else None,
            raw=data,
        )

    # ---------- public API ----------
    async def send_applicant_lead(self, lead: ApplicantLead) -> CrmResult:
        """Phase 6/7 — fired when an applicant is created (self or by operator)."""
        return await self._post("/leads", lead.model_dump(mode="json"))

    async def update_applicant_status(self, payload: ApplicantStatusUpdate) -> CrmResult:
        return await self._post("/leads/status", payload.model_dump(mode="json"))

    async def notify_contract_signed(self, payload: ContractCreatedEvent) -> CrmResult:
        return await self._post("/events/contract-signed", payload.model_dump(mode="json"))


# Convenience singleton-style accessor (no global state — just a factory).
def get_crm_client() -> CrmClient:
    return CrmClient()
