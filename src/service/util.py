from functools import lru_cache
from pathlib import Path
from typing import Optional
import json
import os


def get_data_dir() -> str:
    """Return writable data directory: APP_DATA_DIR when set (packaged app), else project root."""
    app_data = os.environ.get("APP_DATA_DIR")
    if app_data:
        return os.path.abspath(app_data)
    return os.path.abspath(Path(__file__).resolve().parent.parent.parent)


@lru_cache(maxsize=1)
def _load_config() -> dict:
    """Load config once and cache. When APP_DATA_DIR is set (packaged app), DB paths go under APP_DATA_DIR/data/."""
    data_dir = get_data_dir()
    data_subdir = os.path.join(data_dir, "data")
    defaults = {
        "AccountDBPath": os.path.join(data_subdir, "accounts.sqlite"),
        "TransactionDBPath": os.path.join(data_subdir, "transactions.sqlite"),
        "HistoricalPricesDBPath": os.path.join(data_subdir, "historical_prices.sqlite"),
    }
    config_path = Path(__file__).resolve().parent.parent.parent / "config.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}
    # Packaged app: APP_DATA_DIR is set; use our data dir regardless of config file
    if os.environ.get("APP_DATA_DIR"):
        config = {**defaults, **{k: v for k, v in config.items() if k not in defaults}}
    for key, default in defaults.items():
        if key not in config:
            config[key] = default
    return config


def normalize_symbol(s: Optional[str]) -> Optional[str]:
    """Normalize symbol: strip whitespace and uppercase; None or empty -> None."""
    if s is None:
        return None
    stripped = s.strip().upper()
    return stripped if stripped else None


def round2(value: float) -> float:
    """Round to 2 decimal places for monetary values."""
    return round(float(value), 2)
