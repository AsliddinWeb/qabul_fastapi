"""Thin async client for the admission backend REST API.

Handles service-account login, token caching, transparent re-auth on 401,
and the one write the bot performs: setting an application's HEMIS status.
"""

from __future__ import annotations

import logging

import httpx

from bot.config import Config

log = logging.getLogger("bot.api")


class ApiClient:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._token: str | None = None

    async def _login(self) -> str:
        async with httpx.AsyncClient(timeout=self._cfg.request_timeout) as client:
            resp = await client.post(
                f"{self._cfg.api_base_url}/auth/login",
                json={"phone": self._cfg.service_phone, "password": self._cfg.service_password},
            )
            resp.raise_for_status()
            token = resp.json().get("access_token")
        if not token:
            raise RuntimeError("Login succeeded but no access_token in response")
        self._token = token
        log.info("api: logged in as %s", self._cfg.service_phone)
        return token

    async def _token_or_login(self) -> str:
        return self._token or await self._login()

    async def set_hemis_status(self, application_id: str, *, status: str, marked_by: str | None) -> None:
        """POST /applications/{id}/hemis — re-auths once on 401."""
        url = f"{self._cfg.api_base_url}/applications/{application_id}/hemis"
        body = {"status": status, "marked_by": marked_by}
        for attempt in (1, 2):
            token = await self._token_or_login()
            async with httpx.AsyncClient(timeout=self._cfg.request_timeout) as client:
                resp = await client.post(url, json=body, headers={"Authorization": f"Bearer {token}"})
            if resp.status_code == 401 and attempt == 1:
                self._token = None  # expired → re-login and retry once
                continue
            resp.raise_for_status()
            return
