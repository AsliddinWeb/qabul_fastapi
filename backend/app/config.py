from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_secret_key: str = Field(min_length=16)
    app_timezone: str = "Asia/Tashkent"
    app_name: str = "XIU Admission API"
    app_version: str = "0.1.0"

    # --- API ---
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["*"]

    # --- Database ---
    database_url: str  # async (asyncpg)

    @computed_field  # type: ignore[misc]
    @property
    def database_url_sync(self) -> str:
        """Sync URL for Alembic offline mode / management scripts."""
        return self.database_url.replace("+asyncpg", "+psycopg2")

    # --- Redis ---
    redis_url: str = "redis://redis:6379/0"

    # --- JWT ---
    jwt_algorithm: str = "HS256"
    # 8 hours covers a normal working day so operators don't get bounced
    # mid-shift if a refresh-rotation race or a flaky network swallows the
    # background refresh. Refresh tokens stay long (30d) for stale tabs.
    jwt_access_ttl_min: int = 480
    jwt_refresh_ttl_days: int = 30

    # --- OTP ---
    otp_ttl_seconds: int = 120
    otp_length: int = 4
    otp_resend_cooldown_seconds: int = 60
    otp_max_attempts: int = 5

    # --- Eskiz SMS ---
    eskiz_base_url: str = "https://notify.eskiz.uz/api"
    eskiz_email: str = ""
    eskiz_password: str = ""
    eskiz_from: str = "4546"

    # --- CRM (external system, integration-only) ---
    crm_base_url: str = ""
    crm_api_key: str = ""
    crm_timeout_seconds: float = 10.0
    crm_retry_attempts: int = 3
    crm_worker_poll_seconds: float = 5.0

    # --- Files ---
    media_root: str = "/app/media"
    media_url: str = "/media"
    max_upload_size_mb: int = 10

    # --- Public base URL (used for QR codes, public links) ---
    public_base_url: str = "http://localhost:8031"

    # --- Leads SLA worker ---
    leads_sla_hours: int = 72
    leads_sla_poll_seconds: float = 3600

    # --- Telegram notification bot (external, host systemd service) ---
    # Backend PUSHes newly-created applications here so the bot can post them
    # to the operators' group. Empty url = notifications disabled (dev).
    notify_bot_url: str = ""            # e.g. http://host.docker.internal:8090/ingest
    notify_bot_secret: str = ""         # shared secret, sent as X-Ingest-Secret
    notify_bot_timeout_seconds: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
