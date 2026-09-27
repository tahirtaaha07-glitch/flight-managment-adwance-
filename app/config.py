from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://flight_app:change-me-local-only@localhost:5433/flight_ops"
    jwt_secret: str = ""
    app_env: str = "development"
    auto_create_schema: bool = False
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None
    frontend_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    idempotency_retention_hours: int = 48
    price_hold_minutes: int = 45
    waitlist_claim_minutes: int = 30
    refund_escalation_days: int = 3
    overbooking_policy: str = "hard_limit"
    gmail_smtp_host: str = "smtp.gmail.com"
    gmail_smtp_port: int = 587
    gmail_username: str | None = None
    gmail_app_password: str | None = None
    gmail_from: str | None = None
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    frontend_base_url: str = "http://localhost:8000"

    @model_validator(mode="after")
    def validate_production_secret(self):
        if self.app_env == "production" and len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters in production")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if not settings.jwt_secret:
        if settings.app_env == "production":
            raise ValueError("JWT_SECRET is required in production")
        settings.jwt_secret = "local-development-only-change-before-deploy-32"
    return settings
