"""Market data service for quotes and calendar."""

from datetime import datetime
from typing import Optional

from app.core.timezone import now_eastern
from app.domain.views import Quote
from app.providers.market_data_provider import MarketDataProvider


class MarketDataService:
    """
    Service for fetching market data (quotes, calendar).

    Wraps provider with caching and graceful degradation.
    """

    def __init__(
        self,
        provider: MarketDataProvider,
        cache_ttl_seconds: int = 60,
    ):
        self._provider = provider
        self._cache_ttl = cache_ttl_seconds
        self._quote_cache: dict[str, Quote] = {}
        self._cache_time: Optional[datetime] = None

    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """
        Fetch quotes for symbols with caching.

        Returns dict mapping symbol -> Quote (last_price, prev_close, as_of).
        Uses cached data if within TTL; falls back to cache on provider failure.
        """
        if not symbols:
            return {}

        # Normalize symbols
        symbols = [s.upper() for s in symbols]

        # Check cache validity
        if self._is_cache_valid():
            cached_result = {s: self._quote_cache[s] for s in symbols if s in self._quote_cache}
            missing = [s for s in symbols if s not in cached_result]
            if not missing:
                return cached_result
        else:
            missing = symbols
            cached_result = {}

        # Fetch missing quotes from provider
        try:
            new_quotes = self._provider.get_quotes(missing)
            self._quote_cache.update(new_quotes)
            self._cache_time = now_eastern()
            cached_result.update(new_quotes)
        except Exception:
            # Graceful degradation: return whatever is in cache
            pass

        return {s: cached_result[s] for s in symbols if s in cached_result}

    def is_trading_day(self) -> bool:
        """Check if today is a trading day."""
        return self._provider.is_trading_day()

    def previous_trading_day(self) -> str:
        """Get previous trading day as YYYY-MM-DD."""
        return self._provider.previous_trading_day()

    def _is_cache_valid(self) -> bool:
        """Check if cache is within TTL."""
        if not self._cache_time:
            return False
        elapsed = (now_eastern() - self._cache_time).total_seconds()
        return elapsed < self._cache_ttl
