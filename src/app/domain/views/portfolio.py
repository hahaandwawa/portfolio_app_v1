"""View models for portfolio and analysis outputs."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class PositionView:
    """View model for a single holding position."""

    symbol: str
    shares: Decimal
    last_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    prev_close: Optional[Decimal] = None


@dataclass
class Quote:
    """Market quote data for a symbol."""

    symbol: str
    last_price: Decimal
    prev_close: Decimal
    as_of: datetime


@dataclass
class TodayPnlView:
    """Today's profit/loss calculation result."""

    pnl_dollars: Decimal
    pnl_percent: Optional[Decimal] = None
    prev_close_value: Decimal = field(default_factory=lambda: Decimal("0"))
    current_value: Decimal = field(default_factory=lambda: Decimal("0"))
    as_of: Optional[datetime] = None


@dataclass
class AllocationItem:
    """Single item in allocation breakdown."""

    symbol: str
    market_value: Decimal
    percentage: Decimal


@dataclass
class AllocationView:
    """Portfolio allocation breakdown."""

    items: list[AllocationItem] = field(default_factory=list)
    total_value: Decimal = field(default_factory=lambda: Decimal("0"))
    as_of: Optional[datetime] = None


@dataclass
class ImportSummary:
    """Summary of CSV import operation."""

    imported_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list[str] = field(default_factory=list)
    import_batch_id: Optional[str] = None
