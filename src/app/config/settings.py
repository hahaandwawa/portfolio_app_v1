"""Application settings and configuration."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_default_data_dir() -> Path:
    """Return the default data directory based on platform."""
    # Use ~/Documents/Investment App Data as default
    return Path.home() / "Documents" / "Investment App Data"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Investment Management App"
    app_version: str = "0.1.0"

    # Data directory (all app data lives here)
    data_dir: Optional[Path] = None

    # Database URL (derived from data_dir if not set explicitly)
    database_url: Optional[str] = None

    # App behavior
    enforce_cash_balance: bool = False
    log_level: str = "INFO"

    # Market data settings
    market_data_cache_ttl_seconds: int = 60

    def get_data_dir(self) -> Path:
        """Get the data directory, creating it if needed."""
        data_dir = self.data_dir or get_default_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    def get_database_url(self) -> str:
        """Get database URL, deriving from data_dir if not set."""
        if self.database_url:
            return self.database_url
        db_path = self.get_data_dir() / "investment.db"
        return f"sqlite:///{db_path}"

    def get_export_dir(self) -> Path:
        """Get the export directory for CSV files."""
        export_dir = self.get_data_dir() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir

    def get_log_dir(self) -> Path:
        """Get the log directory."""
        log_dir = self.get_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir


# Global settings instance (can be replaced at runtime)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return the current settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def set_settings(settings: Settings) -> None:
    """Set the global settings instance (used by desktop app)."""
    global _settings
    _settings = settings


def reset_settings() -> None:
    """Reset settings to force reload."""
    global _settings
    _settings = None
