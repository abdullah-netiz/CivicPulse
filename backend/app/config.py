from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CivicPulse"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://civicpulse:civicpulse@postgres:5432/civicpulse"
    redis_url: str = "redis://redis:6379/0"
    triage_provider: str = "simulated"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: float = 10.0
    cors_origins: str = "http://localhost:8080"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
