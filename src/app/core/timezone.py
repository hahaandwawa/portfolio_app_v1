"""Timezone utilities for US/Eastern market time."""

from datetime import datetime
from typing import Optional

import pytz
from dateutil import parser as date_parser

EASTERN_TZ = pytz.timezone("US/Eastern")


def now_eastern() -> datetime:
    """Return current time in US/Eastern timezone."""
    return datetime.now(EASTERN_TZ)


def to_eastern(dt: datetime) -> datetime:
    """Convert a datetime to US/Eastern timezone."""
    if dt.tzinfo is None:
        # Assume naive datetime is already Eastern
        return EASTERN_TZ.localize(dt)
    return dt.astimezone(EASTERN_TZ)


def parse_datetime_eastern(value: str, default_tz: Optional[pytz.BaseTzInfo] = None) -> datetime:
    """
    Parse a datetime string and return it in US/Eastern timezone.

    If no timezone is provided in the string, assumes US/Eastern.
    """
    dt = date_parser.parse(value)
    if dt.tzinfo is None:
        tz = default_tz or EASTERN_TZ
        dt = tz.localize(dt)
    return to_eastern(dt)
