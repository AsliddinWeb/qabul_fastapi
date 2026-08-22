"""Bot configuration, loaded from the environment (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    bot_token: str
    group_chat_id: int
    api_base_url: str          # e.g. https://qabul.xiuedu.uz/api/v1
    service_phone: str         # bot's service account (admin role)
    service_password: str
    ingest_secret: str         # shared secret with the backend push
    ingest_host: str
    ingest_port: int
    request_timeout: float


def _req(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


def load_config() -> Config:
    return Config(
        bot_token=_req("BOT_TOKEN"),
        group_chat_id=int(_req("GROUP_CHAT_ID")),
        api_base_url=_req("API_BASE_URL").rstrip("/"),
        service_phone=_req("SERVICE_PHONE"),
        service_password=_req("SERVICE_PASSWORD"),
        ingest_secret=_req("INGEST_SECRET"),
        ingest_host=os.environ.get("INGEST_HOST", "0.0.0.0").strip(),
        ingest_port=int(os.environ.get("INGEST_PORT", "8090")),
        request_timeout=float(os.environ.get("REQUEST_TIMEOUT", "10")),
    )
