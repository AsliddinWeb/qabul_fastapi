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
    """HEMIS's `passport_number` filter expects the FULL passport — series
    letters + number together, e.g. "AE1099577" (NOT just the 7 digits;
    verified against the live student-list). Normalize: strip spaces/dashes,
    uppercase."""
    if not passport_series:
        return None
    v = re.sub(r"[\s\-]", "", passport_series).upper()
    return v or None


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
        """True only if HEMIS has an ACTUAL (synced) student for this passport.

        HEMIS also returns unverified records ("Sinxronizatsiya statusi:
        Tekshirilmagan") when queried by passport, but those carry no
        student_id_number — only verified ("Aktual") students get one. So we
        require at least one matched record WITH a student_id_number.

        Raises on HTTP/network error so the caller can retry or mark errored.
        """
        params = {
            "passport_pin": pinfl,
            "passport_number": passport_number,
            "_student_status": -1,   # any student status (aktual filter is below)
            "limit": 5,              # a person may have >1 record; check them all
        }
        resp = await http.get(
            f"{self._base}/v1/data/student-list",
            params=params,
            headers=self._headers(),
        )
        resp.raise_for_status()
        body = resp.json()
        items = (body.get("data") or {}).get("items") or []
        return any(it.get("student_id_number") for it in items)
