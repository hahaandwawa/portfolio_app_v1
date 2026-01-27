"""
Unit tests for MarketDataService.

Tests cover:
- Getting quotes from provider
- Quote caching behavior
- Cache TTL expiration
- Graceful degradation on provider failure
- Fallback to cached data
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.services import MarketDataService
from app.domain.views import Quote
from app.core.timezone import EASTERN_TZ

from tests.conftest import (
    DeterministicMarketProvider,
    FailingMarketProvider,
    eastern_datetime,
)


# =============================================================================
# BASIC QUOTE RETRIEVAL TESTS
# =============================================================================


class TestGetQuotes:
    """Tests for basic quote retrieval."""

    def test_get_quotes_returns_quote_data(
        self,
        deterministic_provider: DeterministicMarketProvider,
    ):
        """
        GIVEN a market data provider with AAPL quote
        WHEN I call get_quotes(["AAPL"])
        THEN result contains Quote with last_price, prev_close, as_of
        """
        service = MarketDataService(
            provider=deterministic_provider,
            cache_ttl_seconds=60,
        )

        quotes = service.get_quotes(["AAPL"])

        assert "AAPL" in quotes
        quote = quotes["AAPL"]
        assert quote.symbol == "AAPL"
        assert quote.last_price == Decimal("185.50")
        assert quote.prev_close == Decimal("184.25")
        assert quote.as_of is not None

    def test_get_quotes_multiple_symbols(
        self,
        deterministic_provider: DeterministicMarketProvider,
    ):
        """
        GIVEN a provider with multiple symbols
        WHEN I request multiple symbols
        THEN all quotes are returned
        """
        service = MarketDataService(
            provider=deterministic_provider,
            cache_ttl_seconds=60,
        )

        quotes = service.get_quotes(["AAPL", "MSFT", "GOOGL"])

        assert len(quotes) == 3
        assert "AAPL" in quotes
        assert "MSFT" in quotes
        assert "GOOGL" in quotes

    def test_get_quotes_empty_list_returns_empty_dict(
        self,
        deterministic_provider: DeterministicMarketProvider,
    ):
        """
        GIVEN any provider
        WHEN I call get_quotes([])
        THEN result is empty dict
        """
        service = MarketDataService(
            provider=deterministic_provider,
            cache_ttl_seconds=60,
        )

        quotes = service.get_quotes([])

        assert quotes == {}

    def test_get_quotes_normalizes_to_uppercase(
        self,
        deterministic_provider: DeterministicMarketProvider,
    ):
        """
        GIVEN a provider
        WHEN I request with lowercase symbols
        THEN symbols are normalized to uppercase
        """
        service = MarketDataService(
            provider=deterministic_provider,
            cache_ttl_seconds=60,
        )

        quotes = service.get_quotes(["aapl", "msft"])

        assert "AAPL" in quotes
        assert "MSFT" in quotes

    def test_get_quotes_unknown_symbol_not_in_result(
        self,
        deterministic_provider: DeterministicMarketProvider,
    ):
        """
        GIVEN provider only knows certain symbols
        WHEN I request an unknown symbol
        THEN unknown symbol is omitted from result
        """
        service = MarketDataService(
            provider=deterministic_provider,
            cache_ttl_seconds=60,
        )

        quotes = service.get_quotes(["AAPL", "UNKNOWN_SYMBOL"])

        assert "AAPL" in quotes
        assert "UNKNOWN_SYMBOL" not in quotes


# =============================================================================
# CACHING TESTS
# =============================================================================


class TestQuoteCaching:
    """Tests for quote caching behavior."""

    def test_cache_hit_does_not_call_provider(self):
        """
        GIVEN cache TTL is 60 seconds
        WHEN I call get_quotes twice within TTL
        THEN provider is called only once
        """
        mock_provider = MagicMock()
        mock_provider.get_quotes.return_value = {
            "AAPL": Quote(
                symbol="AAPL",
                last_price=Decimal("185.50"),
                prev_close=Decimal("184.25"),
                as_of=eastern_datetime(2024, 6, 15, 14, 0, 0),
            )
        }

        service = MarketDataService(
            provider=mock_provider,
            cache_ttl_seconds=60,
        )

        # First call
        quotes1 = service.get_quotes(["AAPL"])
        # Second call within TTL
        quotes2 = service.get_quotes(["AAPL"])

        # Provider should be called only once
        assert mock_provider.get_quotes.call_count == 1
        assert quotes1 == quotes2

    def test_cache_returns_cached_data(self):
        """
        GIVEN a quote is cached
        WHEN I request the same symbol
        THEN cached quote is returned
        """
        mock_provider = MagicMock()
        original_quote = Quote(
            symbol="AAPL",
            last_price=Decimal("185.50"),
            prev_close=Decimal("184.25"),
            as_of=eastern_datetime(2024, 6, 15, 14, 0, 0),
        )
        mock_provider.get_quotes.return_value = {"AAPL": original_quote}

        service = MarketDataService(
            provider=mock_provider,
            cache_ttl_seconds=60,
        )

        service.get_quotes(["AAPL"])
        # Change provider response (shouldn't affect cached result)
        mock_provider.get_quotes.return_value = {
            "AAPL": Quote(
                symbol="AAPL",
                last_price=Decimal("999.99"),
                prev_close=Decimal("998.00"),
                as_of=eastern_datetime(2024, 6, 15, 14, 1, 0),
            )
        }
        quotes = service.get_quotes(["AAPL"])

        # Should still return original cached quote
        assert quotes["AAPL"].last_price == Decimal("185.50")

    def test_cache_miss_for_new_symbol_calls_provider(self):
        """
        GIVEN AAPL is cached
        WHEN I request AAPL and MSFT
        THEN provider is called for MSFT only
        """
        call_count = 0
        requested_symbols = []

        def mock_get_quotes(symbols):
            nonlocal call_count, requested_symbols
            call_count += 1
            requested_symbols.extend(symbols)
            result = {}
            for s in symbols:
                result[s] = Quote(
                    symbol=s,
                    last_price=Decimal("100.00"),
                    prev_close=Decimal("99.00"),
                    as_of=eastern_datetime(2024, 6, 15, 14, 0, 0),
                )
            return result

        mock_provider = MagicMock()
        mock_provider.get_quotes = mock_get_quotes

        service = MarketDataService(
            provider=mock_provider,
            cache_ttl_seconds=60,
        )

        # Cache AAPL
        service.get_quotes(["AAPL"])
        # Request both
        quotes = service.get_quotes(["AAPL", "MSFT"])

        assert call_count == 2
        assert "MSFT" in requested_symbols
        assert len(quotes) == 2

    def test_cache_expiry_calls_provider_again(self):
        """
        GIVEN cache TTL is very short (simulated)
        WHEN cache expires
        THEN provider is called again
        """
        mock_provider = MagicMock()
        mock_provider.get_quotes.return_value = {
            "AAPL": Quote(
                symbol="AAPL",
                last_price=Decimal("185.50"),
                prev_close=Decimal("184.25"),
                as_of=eastern_datetime(2024, 6, 15, 14, 0, 0),
            )
        }

        service = MarketDataService(
            provider=mock_provider,
            cache_ttl_seconds=1,  # 1 second TTL
        )

        # First call
        service.get_quotes(["AAPL"])
        assert mock_provider.get_quotes.call_count == 1

        # Manually invalidate cache by setting old cache time
        service._cache_time = eastern_datetime(2024, 6, 15, 13, 0, 0)  # Old time

        # Second call after "expiry"
        service.get_quotes(["AAPL"])
        assert mock_provider.get_quotes.call_count == 2


# =============================================================================
# FALLBACK / GRACEFUL DEGRADATION TESTS
# =============================================================================


class TestGracefulDegradation:
    """Tests for graceful degradation on provider failure."""

    def test_fallback_to_cache_on_provider_failure(self):
        """
        GIVEN AAPL quote is cached from previous call
        AND provider is now failing
        WHEN I call get_quotes
        THEN cached quote is returned
        """
        call_count = 0

        def flaky_get_quotes(symbols):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call succeeds
                return {
                    "AAPL": Quote(
                        symbol="AAPL",
                        last_price=Decimal("185.50"),
                        prev_close=Decimal("184.25"),
                        as_of=eastern_datetime(2024, 6, 15, 14, 0, 0),
                    )
                }
            else:
                # Subsequent calls fail
                raise ConnectionError("Network unavailable")

        mock_provider = MagicMock()
        mock_provider.get_quotes = flaky_get_quotes

        service = MarketDataService(
            provider=mock_provider,
            cache_ttl_seconds=1,  # Short TTL to force refetch
        )

        # First call - succeeds and caches
        quotes1 = service.get_quotes(["AAPL"])
        assert quotes1["AAPL"].last_price == Decimal("185.50")

        # Expire cache
        service._cache_time = eastern_datetime(2024, 6, 15, 13, 0, 0)

        # Second call - provider fails, returns cached
        quotes2 = service.get_quotes(["AAPL"])
        assert quotes2["AAPL"].last_price == Decimal("185.50")

    def test_provider_failure_with_no_cache_returns_empty(self):
        """
        GIVEN no cached data
        AND provider is failing
        WHEN I call get_quotes
        THEN empty dict is returned (graceful degradation)
        """
        failing_provider = FailingMarketProvider()

        service = MarketDataService(
            provider=failing_provider,
            cache_ttl_seconds=60,
        )

        quotes = service.get_quotes(["AAPL"])

        assert quotes == {}

    def test_partial_cache_on_mixed_request(self):
        """
        GIVEN AAPL is cached but not MSFT
        AND provider fails
        WHEN I request both
        THEN only AAPL (cached) is returned
        """
        call_count = 0

        def flaky_get_quotes(symbols):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "AAPL": Quote(
                        symbol="AAPL",
                        last_price=Decimal("185.50"),
                        prev_close=Decimal("184.25"),
                        as_of=eastern_datetime(2024, 6, 15, 14, 0, 0),
                    )
                }
            raise ConnectionError("Network unavailable")

        mock_provider = MagicMock()
        mock_provider.get_quotes = flaky_get_quotes

        service = MarketDataService(
            provider=mock_provider,
            cache_ttl_seconds=60,
        )

        # Cache AAPL
        service.get_quotes(["AAPL"])

        # Request both (MSFT will fail)
        quotes = service.get_quotes(["AAPL", "MSFT"])

        # Only AAPL available
        assert "AAPL" in quotes
        assert "MSFT" not in quotes


# =============================================================================
# TRADING DAY / CALENDAR TESTS
# =============================================================================


class TestTradingCalendar:
    """Tests for trading day information."""

    def test_is_trading_day_delegates_to_provider(
        self,
        deterministic_provider: DeterministicMarketProvider,
    ):
        """
        GIVEN a provider
        WHEN I call is_trading_day
        THEN result comes from provider
        """
        service = MarketDataService(
            provider=deterministic_provider,
            cache_ttl_seconds=60,
        )

        result = service.is_trading_day()

        assert result is True  # Deterministic provider returns True

    def test_previous_trading_day_delegates_to_provider(
        self,
        deterministic_provider: DeterministicMarketProvider,
    ):
        """
        GIVEN a provider
        WHEN I call previous_trading_day
        THEN result comes from provider
        """
        service = MarketDataService(
            provider=deterministic_provider,
            cache_ttl_seconds=60,
        )

        result = service.previous_trading_day()

        assert result == "2024-06-14"  # Deterministic provider value


# =============================================================================
# STUB PROVIDER TESTS
# =============================================================================


class TestStubProvider:
    """Tests for the stub market data provider."""

    def test_stub_provider_known_symbols(self):
        """
        GIVEN StubMarketDataProvider
        WHEN I request known symbols
        THEN deterministic prices are returned
        """
        from app.providers.stub_provider import StubMarketDataProvider

        provider = StubMarketDataProvider(seed=42)

        quotes = provider.get_quotes(["AAPL", "MSFT"])

        assert quotes["AAPL"].last_price == Decimal("185.50")
        assert quotes["AAPL"].prev_close == Decimal("184.25")
        assert quotes["MSFT"].last_price == Decimal("378.25")
        assert quotes["MSFT"].prev_close == Decimal("376.80")

    def test_stub_provider_unknown_symbol_generates_price(self):
        """
        GIVEN StubMarketDataProvider
        WHEN I request an unknown symbol
        THEN a generated price is returned
        """
        from app.providers.stub_provider import StubMarketDataProvider

        provider = StubMarketDataProvider(seed=42)

        quotes = provider.get_quotes(["UNKNOWN"])

        assert "UNKNOWN" in quotes
        assert quotes["UNKNOWN"].last_price > Decimal("0")
        assert quotes["UNKNOWN"].prev_close > Decimal("0")

    def test_stub_provider_deterministic_with_seed(self):
        """
        GIVEN two StubMarketDataProviders with same seed
        WHEN I request same symbol
        THEN same prices are returned
        """
        from app.providers.stub_provider import StubMarketDataProvider

        provider1 = StubMarketDataProvider(seed=42)
        provider2 = StubMarketDataProvider(seed=42)

        quotes1 = provider1.get_quotes(["RANDOMSYM"])
        quotes2 = provider2.get_quotes(["RANDOMSYM"])

        assert quotes1["RANDOMSYM"].last_price == quotes2["RANDOMSYM"].last_price
