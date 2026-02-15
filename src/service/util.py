from functools import lru_cache
from pathlib import Path
from typing import Optional
import json


@lru_cache(maxsize=1)
def _load_config() -> dict:
    """Load config.json once and cache for the process lifetime."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config.json"
    with open(config_path) as f:
        return json.load(f)


def normalize_symbol(s: Optional[str]) -> Optional[str]:
    """Normalize symbol: strip whitespace and uppercase; None or empty -> None."""
    if s is None:
        return None
    stripped = s.strip().upper()
    return stripped if stripped else None


def round2(value: float) -> float:
    """Round to 2 decimal places for monetary values."""
    return round(float(value), 2)
