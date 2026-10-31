from functools import lru_cache

from pydantic import SecretStr
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
    public_base_url: str = "https://localhost:8443"

    login_max_attempts: int = 10
    login_window_seconds: int = 300

    # Created on startup when the database has no users yet.
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: SecretStr | None = None

    llm_provider: str = "fake"
    embedding_provider: str = "fake"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
