# app/core/config.py
# ─────────────────────────────────────────────────────────────
# All configuration loaded from environment / .env file.
# Pydantic-settings validates types and raises clear errors
# if required values are missing — fail fast on bad config.
# ─────────────────────────────────────────────────────────────

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl, field_validator
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",           # silently ignore unknown env vars
    )

    # ── App ────────────────────────────────────────────────────
    APP_NAME: str = "AttendIQ ERP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    # Allowed browser origins for CORS — comma-separated in .env
    # e.g. CORS_ORIGINS=http://localhost:5173,https://your-portal.com
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # ── Database ───────────────────────────────────────────────
    # Full async postgres URL:
    #   postgresql+asyncpg://user:password@host:5432/dbname
    DATABASE_URL: str

    # ── JWT ────────────────────────────────────────────────────
    # Generate with: openssl rand -hex 32
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    # How long access tokens last (minutes) — keep short for security
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # How long refresh tokens last (days)
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Device auth ────────────────────────────────────────────
    # This is the shared secret all Pi devices send in X-Api-Key header.
    # Matches ERP_API_KEY in the Pi's .env file.
    DEVICE_API_KEY: str

    # ── First-run super admin (used by init_db only) ───────────
    FIRST_ADMIN_EMAIL: str = "admin@company.com"
    FIRST_ADMIN_PASSWORD: str = "changeme123"   # MUST change after first login
    FIRST_ADMIN_NAME: str = "System Admin"

    # ── Attendance business rules ──────────────────────────────
    # Default company shift start time (HH:MM 24h)
    DEFAULT_SHIFT_START: str = "09:00"
    # Minutes after shift start before someone is marked "late"
    LATE_GRACE_MINUTES: int = 15
    # Minimum minutes between punch-in and punch-out to count as valid shift
    MIN_SHIFT_MINUTES: int = 5

    # ── Notifications (Phase 5, configured now) ────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFY_FROM_EMAIL: str = "noreply@company.com"

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must start with postgresql+asyncpg:// "
                "(not postgresql:// — the async driver requires +asyncpg)"
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns cached settings singleton.
    Use as a FastAPI dependency: settings = Depends(get_settings)
    Or import directly: from app.core.config import settings
    """
    return Settings()


# Module-level singleton for imports throughout the app
settings = get_settings()
