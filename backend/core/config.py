"""
core/config.py

Centralised application settings using Pydantic BaseSettings.
All values are loaded from environment variables (or .env file).
Config is validated at startup — app FAILS FAST on missing/invalid config.
Never import raw os.environ elsewhere; always use `from core.config import settings`.
"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Single source of truth for all environment-based configuration.
    Validated at startup via `get_settings()`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # silently ignore unknown env vars
    )

    # ── App ───────────────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "AI Appointment Platform"
    DEBUG: bool = False
    SECRET_KEY: str

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://...

    # ── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str  # redis://host:6379/0

    # ── Supabase Auth ────────────────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    SUPABASE_JWT_SECRET: str

    # ── LLM Provider (EuriAI — OpenAI-compatible) ────────────────────────────
    OPENAI_API_KEY: str                              # EuriAI key goes here
    OPENAI_BASE_URL: str = "https://api.euron.one/api/v1/euri"
    OPENAI_MODEL: str = "gpt-4.1"

    # ── Twilio ───────────────────────────────────────────────────────────────
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    TWILIO_PHONE_FROM: str
    TWILIO_WHATSAPP_FROM: str

    # ── SMTP Email (Gmail) ────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""           # Gmail address (platform default)
    SMTP_PASSWORD: str = ""       # Gmail App Password (16 chars)
    SMTP_FROM_NAME: str = "AppointAI"

    # ── Google Calendar ───────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    # ── Stripe ────────────────────────────────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_GROWTH: str = ""
    STRIPE_PRICE_PRO: str = ""

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_CHAT: int = 100        # per minute per tenant
    RATE_LIMIT_BOOKING: int = 30
    RATE_LIMIT_NOTIFICATION: int = 60

    # ── Celery ────────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # ── Trial Config ──────────────────────────────────────────────────────────
    TRIAL_DAYS: int = 14
    TRIAL_MAX_EXECUTIONS: int = 100

    # ── Admin (Platform Super Admin) ──────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@appointai.in"
    ADMIN_PASSWORD_HASH: str = ""  # bcrypt hash of admin password; set in .env

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters for security.")
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def database_url_must_use_asyncpg(cls, v: str) -> str:
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use 'postgresql+asyncpg://' for async support."
            )
        return v

    def get_allowed_origins(self) -> List[str]:
        """Parse comma-separated ALLOWED_ORIGINS into a list."""
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns the singleton Settings instance.
    Cached so env vars are only read once.
    Application startup calls this — any missing required var raises ValueError immediately.
    """
    return Settings()


# Module-level shortcut used across the codebase
settings: Settings = get_settings()
