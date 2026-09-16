"""HEMIS (student.xiuedu.uz) client — checks whether an applicant already
exists as an enrolled student, matched by passport PIN + passport number.

Backend-only: the HEMIS "Backend API" group is CORS-blocked for browsers and
rate-limited to 10 req/sec per IP, so this is called from a server-side
background job (never the frontend).

Auth: a static Bearer token issued in the HEMIS admin dashboard
(settings.hemis_api_token).
"""

from __future__ import annotations

import re

import httpx

from app.config import settings


def extract_passport_number(passport_series: str | None) -> str | None:
    """Applicants store passport as "AA1234567" (2-letter series + 7 digits).
    HEMIS wants just the numeric part. Falls back to all digits found."""
    if not passport_series:
        return None
    digits = re.sub(r"\D", "", passport_series)
    return digits or None


class HemisClient:
    def __init__(self) -> None:
        self._base = settings.hemis_base_url.rstrip("/")
        self._token = settings.hemis_api_token

    @property
    def configured(self) -> bool:
        return bool(self._token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    async def student_found(
        self, http: httpx.AsyncClient, *, pinfl: str, passport_number: str
    ) -> bool:
        """True if HEMIS returns at least one student for this passport
        PIN + number. Raises on HTTP/network error so the caller can retry
        or mark the row as errored."""
        params = {
            "passport_pin": pinfl,
            "passport_number": passport_number,
            "_student_status": -1,   # any status (graduated/expelled/active)
            "limit": 1,
        }
        resp = await http.get(
            f"{self._base}/v1/data/student-list",
            params=params,
            headers=self._headers(),
        )
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data") or {}
        items = data.get("items") or []
        return len(items) > 0
