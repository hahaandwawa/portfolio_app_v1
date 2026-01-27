"""Stub market data provider for offline/testing use."""

from decimal import Decimal
from datetime import datetime
import random

from app.core.timezone import now_eastern
from app.domain.views import Quote


# Deterministic fake prices for common symbols
_STUB_PRICES: dict[str, tuple[Decimal, Decimal]] = {
    "AAPL": (Decimal("185.50"), Decimal("184.25")),
    "GOOGL": (Decimal("142.75"), Decimal("141.50")),
    "MSFT": (Decimal("378.25"), Decimal("376.80")),
    "AMZN": (Decimal("178.50"), Decimal("177.25")),
    "TSLA": (Decimal("248.75"), Decimal("250.10")),
    "NVDA": (Decimal("485.25"), Decimal("482.50")),
    "META": (Decimal("505.50"), Decimal("502.75")),
    "SPY": (Decimal("485.25"), Decimal("484.10")),
    "QQQ": (Decimal("418.75"), Decimal("417.50")),
    "VTI": (Decimal("252.30"), Decimal("251.80")),
}


class StubMarketDataProvider:
    """
    Stub provider with deterministic fake data for offline operation.

    Uses predefined prices for common symbols; generates random prices for unknown symbols.
    """

    def __init__(self, seed: int = 42):
        """Initialize with optional random seed for reproducibility."""
        self._rng = random.Random(seed)

    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Return stub quotes for requested symbols."""
        as_of = now_eastern()
        result: dict[str, Quote] = {}

        for symbol in symbols:
            upper_symbol = symbol.upper()
            if upper_symbol in _STUB_PRICES:
                last_price, prev_close = _STUB_PRICES[upper_symbol]
            else:
                # Generate deterministic random price based on symbol
                base_price = Decimal(str(50 + self._rng.random() * 200))
                last_price = base_price.quantize(Decimal("0.01"))
                change_pct = Decimal(str((self._rng.random() - 0.5) * 0.04))
                prev_close = (last_price / (1 + change_pct)).quantize(Decimal("0.01"))

            result[upper_symbol] = Quote(
                symbol=upper_symbol,
                last_price=last_price,
                prev_close=prev_close,
                as_of=as_of,
            )

        return result

    def is_trading_day(self) -> bool:
        """Stub: always returns True for simplicity."""
        # TODO: Implement real market calendar check
        return True

    def previous_trading_day(self) -> str:
        """Stub: returns yesterday's date (simplified)."""
        # TODO: Implement real market calendar lookup
        from datetime import timedelta
        yesterday = now_eastern() - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")
