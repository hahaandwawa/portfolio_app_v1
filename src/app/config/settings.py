"""Application settings and configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Investment Management App"
    database_url: str = "sqlite:///./investment.db"
    enforce_cash_balance: bool = False
    log_level: str = "INFO"

    # Market data settings
    market_data_cache_ttl_seconds: int = 60


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
