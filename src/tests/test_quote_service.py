"""
Tests for QuoteService: cache, TTL, per-symbol failure, timeout.
Uses mocks to avoid hitting Yahoo Finance.
"""
import time
from unittest.mock import MagicMock, patch

import pytest

from src.service.quote_service import (
    QuoteService,
    _fetch_quotes_impl,
    _safe_quote_for_symbol,
    DEFAULT_TTL_SECONDS,
)


# -----------------------------------------------------------------------------
# _safe_quote_for_symbol (unit)
# -----------------------------------------------------------------------------


class TestSafeQuoteForSymbol:
    """_safe_quote_for_symbol returns (price, name, previous_close) or (None, symbol, None) on error."""

    def test_extracts_current_price_and_long_name(self):
        tickers = MagicMock()
        tickers.tickers = {
            "AAPL": MagicMock(info={"currentPrice": 175.5, "longName": "Apple Inc."}),
        }
        price, name, prev_close = _safe_quote_for_symbol("AAPL", tickers)
        assert price == 175.5
        assert name == "Apple Inc."
        assert prev_close is None

    def test_extracts_previous_close_when_present(self):
        tickers = MagicMock()
        tickers.tickers = {
            "AAPL": MagicMock(info={
                "currentPrice": 180.0,
                "longName": "Apple Inc.",
                "previousClose": 175.25,
            }),
        }
        price, name, prev_close = _safe_quote_for_symbol("AAPL", tickers)
        assert price == 180.0
        assert name == "Apple Inc."
        assert prev_close == 175.25

    def test_fallback_regular_market_previous_close(self):
        tickers = MagicMock()
        tickers.tickers = {
            "X": MagicMock(info={
                "regularMarketPrice": 22.0,
                "regularMarketPreviousClose": 21.5,
                "shortName": "X Corp",
            }),
        }
        price, name, prev_close = _safe_quote_for_symbol("X", tickers)
        assert price == 22.0
        assert name == "X Corp"
        assert prev_close == 21.5

    def test_fallback_regular_market_price(self):
        tickers = MagicMock()
        tickers.tickers = {
            "X": MagicMock(info={"regularMarketPrice": 22.0, "shortName": "X Corp"}),
        }
        price, name, prev_close = _safe_quote_for_symbol("X", tickers)
        assert price == 22.0
        assert name == "X Corp"
        assert prev_close is None

    def test_fallback_display_name_to_symbol(self):
        tickers = MagicMock()
        tickers.tickers = {
            "Y": MagicMock(info={"currentPrice": 10.0}),  # no longName/shortName
        }
        price, name, prev_close = _safe_quote_for_symbol("Y", tickers)
        assert price == 10.0
        assert name == "Y"
        assert prev_close is None

    def test_missing_ticker_returns_none_and_symbol(self):
        tickers = MagicMock()
        tickers.tickers = {}
        price, name, prev_close = _safe_quote_for_symbol("UNKNOWN", tickers)
        assert price is None
        assert name == "UNKNOWN"
        assert prev_close is None

    def test_exception_returns_none_and_symbol(self):
        tickers = MagicMock()
        tickers.tickers = {"Z": MagicMock()}
        tickers.tickers["Z"].info = None  # will cause TypeError or similar when we .get
        price, name, prev_close = _safe_quote_for_symbol("Z", tickers)
        assert price is None
        assert name == "Z"
        assert prev_close is None


# -----------------------------------------------------------------------------
# QuoteService with mocked yfinance
# -----------------------------------------------------------------------------


@patch("src.service.quote_service._get_yf")
def test_get_quotes_returns_price_name_and_previous_close(mock_get_yf):
    """get_quotes calls yfinance and returns current_price, display_name, and previous_close per symbol."""
    mock_yf = MagicMock()
    mock_tickers = MagicMock()
    mock_tickers.tickers = {
        "AAPL": MagicMock(info={
            "currentPrice": 180.0,
            "longName": "Apple Inc.",
            "previousClose": 178.5,
        }),
        "MSFT": MagicMock(info={"currentPrice": 400.0, "longName": "Microsoft Corporation"}),
    }
    mock_yf.Tickers.return_value = mock_tickers
    mock_get_yf.return_value = mock_yf

    svc = QuoteService(ttl_seconds=60, fetch_timeout_seconds=5)
    result = svc.get_quotes(["AAPL", "MSFT"])

    assert result["AAPL"]["current_price"] == 180.0
    assert result["AAPL"]["display_name"] == "Apple Inc."
    assert result["AAPL"]["previous_close"] == 178.5
    assert result["MSFT"]["current_price"] == 400.0
    assert result["MSFT"]["display_name"] == "Microsoft Corporation"
    assert result["MSFT"]["previous_close"] is None


def test_get_quotes_empty_list_returns_empty():
    svc = QuoteService()
    assert svc.get_quotes([]) == {}


@patch("src.service.quote_service._get_yf")
def test_get_quotes_cache_hit_does_not_call_yfinance(mock_get_yf):
    mock_yf = MagicMock()
    mock_tickers = MagicMock()
    mock_tickers.tickers = {"AAPL": MagicMock(info={"currentPrice": 100.0, "longName": "Apple"})}
    mock_yf.Tickers.return_value = mock_tickers
    mock_get_yf.return_value = mock_yf

    svc = QuoteService(ttl_seconds=2, fetch_timeout_seconds=5)
    first = svc.get_quotes(["AAPL"])
    assert first["AAPL"]["current_price"] == 100.0

    # Second call within TTL: cache hit, yfinance not called again (Tickers called once)
    second = svc.get_quotes(["AAPL"])
    assert second["AAPL"]["current_price"] == 100.0
    assert mock_yf.Tickers.call_count == 1


@patch("src.service.quote_service._get_yf")
def test_get_quotes_cache_expires_after_ttl(mock_get_yf):
    mock_yf = MagicMock()
    mock_tickers = MagicMock()
    mock_tickers.tickers = {"AAPL": MagicMock(info={"currentPrice": 99.0, "longName": "Apple"})}
    mock_yf.Tickers.return_value = mock_tickers
    mock_get_yf.return_value = mock_yf

    svc = QuoteService(ttl_seconds=0.1, fetch_timeout_seconds=5)  # 100ms TTL
    svc.get_quotes(["AAPL"])
    time.sleep(0.15)
    svc.get_quotes(["AAPL"])
    # Tickers should be called twice (first fetch, then after TTL expiry)
    assert mock_yf.Tickers.call_count == 2


@patch("src.service.quote_service._get_yf")
def test_get_quotes_failure_returns_none_price_and_symbol_as_name(mock_get_yf):
    """One symbol raises when accessed; that symbol gets current_price=None, display_name=symbol, previous_close=None."""
    bad_ticker = MagicMock()
    type(bad_ticker).info = property(lambda s: (_ for _ in ()).throw(ValueError("quote failed")))
    mock_yf = MagicMock()
    mock_tickers = MagicMock()
    mock_tickers.tickers = {
        "GOOD": MagicMock(info={"currentPrice": 50.0, "longName": "Good Inc."}),
        "BAD": bad_ticker,
    }
    mock_yf.Tickers.return_value = mock_tickers
    mock_get_yf.return_value = mock_yf

    svc = QuoteService(fetch_timeout_seconds=5)
    result = svc.get_quotes(["GOOD", "BAD"])

    assert result["GOOD"]["current_price"] == 50.0
    assert result["GOOD"]["display_name"] == "Good Inc."
    assert result["GOOD"]["previous_close"] is None
    assert result["BAD"]["current_price"] is None
    assert result["BAD"]["display_name"] == "BAD"
    assert result["BAD"]["previous_close"] is None


@patch("src.service.quote_service._get_yf")
def test_get_quotes_exception_during_fetch_returns_none_and_symbol(mock_get_yf):
    """When fetch raises (e.g. timeout), get_quotes returns current_price=None, display_name=symbol, previous_close=None."""
    mock_get_yf.side_effect = Exception("network or timeout")

    svc = QuoteService(fetch_timeout_seconds=5)
    result = svc.get_quotes(["AAPL", "MSFT"])

    assert result["AAPL"]["current_price"] is None
    assert result["AAPL"]["display_name"] == "AAPL"
    assert result["AAPL"]["previous_close"] is None
    assert result["MSFT"]["current_price"] is None
    assert result["MSFT"]["display_name"] == "MSFT"
    assert result["MSFT"]["previous_close"] is None
