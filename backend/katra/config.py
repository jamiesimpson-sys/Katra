from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration and secrets come from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_prefix="KATRA_", env_file=".env", extra="ignore")

    database_url: SecretStr
    environment: str = "development"

    session_ttl_hours: int = 12
    invite_ttl_hours: int = 72
    session_cookie_name: str = "katra_session"
    csrf_cookie_name: str = "katra_csrf"
    # Used in invite links. Unset = derive from the incoming request (works behind a proxy).
    public_base_url: str | None = None
    # If set, the API also serves the built SPA from here (single-container deploys).
    static_dir: str | None = None

    login_max_attempts: int = 10
    login_window_seconds: int = 300

    # Created on startup when the database has no users yet.
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: SecretStr | None = None

    llm_provider: str = "fake"
    embedding_provider: str = "fake"

    @field_validator("database_url", mode="before")
    @classmethod
    def _use_psycopg_driver(cls, v: object) -> object:
        # Hosting providers hand out postgres:// or postgresql:// URLs; we need psycopg 3.
        if isinstance(v, str):
            for prefix in ("postgres://", "postgresql://"):
                if v.startswith(prefix):
                    return "postgresql+psycopg://" + v[len(prefix) :]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
