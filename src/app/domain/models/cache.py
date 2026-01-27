"""Cache models for derived portfolio state."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class PositionCache:
    """
    Derived holdings cache per account/symbol.

    IMPORTANT: Never edit directly; always rebuild from ledger.
    """

    account_id: str
    symbol: str
    shares: Decimal = field(default_factory=lambda: Decimal("0"))
    last_rebuilt_at_est: Optional[datetime] = field(default=None)


@dataclass
class CashCache:
    """
    Derived cash balance cache per account.

    IMPORTANT: Never edit directly; always rebuild from ledger.
    """

    account_id: str
    cash_balance: Decimal = field(default_factory=lambda: Decimal("0"))
    last_rebuilt_at_est: Optional[datetime] = field(default=None)
