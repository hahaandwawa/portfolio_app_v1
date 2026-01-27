"""Market data provider protocol and base types."""

from typing import Protocol

from app.domain.views import Quote


class MarketDataProvider(Protocol):
    """
    Protocol for market data providers.

    Implementations should fetch real-time quotes (last_price, prev_close).
    Graceful degradation: return cached data with timestamp on API failure.
    """

    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """
        Fetch quotes for multiple symbols.

        Returns dict mapping symbol -> Quote with last_price, prev_close, as_of.
        Missing symbols are omitted from result.
        """
        ...

    def is_trading_day(self) -> bool:
        """Check if today is a trading day."""
        ...

    def previous_trading_day(self) -> str:
        """Return the previous trading day as YYYY-MM-DD string."""
        ...
