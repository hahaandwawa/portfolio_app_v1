"""
Quote service: fetch current price and display name from Yahoo Finance via yfinance.
In-memory cache with TTL; degrades gracefully on timeout or per-symbol failure.
"""

import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Optional

from src.service.util import round2

# Lazy import so tests can patch before import
def _get_yf():
    import yfinance as yf
    return yf


DEFAULT_TTL_SECONDS = 120
DEFAULT_FETCH_TIMEOUT_SECONDS = 10


def _safe_quote_for_symbol(symbol: str, tickers_obj) -> tuple[Optional[float], str, Optional[float]]:
    """
    Get current_price, display_name, and previous_close for one symbol from a yfinance Tickers object.
    Returns (current_price, display_name, previous_close). On any error, returns (None, symbol, None).
    """
    try:
        ticker = tickers_obj.tickers.get(symbol)
        if ticker is None:
            return (None, symbol, None)
        info = ticker.info
        if not isinstance(info, dict):
            return (None, symbol, None)
        # Price: currentPrice preferred, then regularMarketPrice
        price = info.get("currentPrice")
        if price is None:
            price = info.get("regularMarketPrice")
        if price is not None:
            try:
                price = round2(float(price))
            except (TypeError, ValueError):
                price = None
        # Name: longName preferred, then shortName
        name = (info.get("longName") or info.get("shortName") or "").strip() or symbol
        # Previous close: previousClose or regularMarketPreviousClose (yfinance)
        prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
        if prev_close is not None:
            try:
                prev_close = round2(float(prev_close))
            except (TypeError, ValueError):
                prev_close = None
        return (price, name, prev_close)
    except Exception:
        return (None, symbol, None)


def _fetch_quotes_impl(symbols: list[str]) -> dict[str, dict]:
    """Call yfinance and return dict symbol -> { current_price, display_name, previous_close }. No cache."""
    if not symbols:
        return {}
    yf = _get_yf()
    tickers = yf.Tickers(" ".join(symbols))
    result = {}
    for sym in symbols:
        price, name, prev_close = _safe_quote_for_symbol(sym, tickers)
        result[sym] = {"current_price": price, "display_name": name, "previous_close": prev_close}
    return result


class QuoteService:
    """
    Fetches quotes from Yahoo Finance via yfinance.
    In-memory cache per symbol with configurable TTL.
    """

    def __init__(
        self,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        fetch_timeout_seconds: float = DEFAULT_FETCH_TIMEOUT_SECONDS,
    ):
        self._ttl = ttl_seconds
        self._fetch_timeout = fetch_timeout_seconds
        # Cache: symbol -> (current_price, display_name, previous_close, cached_at)
        self._cache: dict[str, tuple[Optional[float], str, Optional[float], float]] = {}

    def get_quotes(self, symbols: list[str]) -> dict[str, dict]:
        """
        Return for each symbol: { "current_price": float | None, "display_name": str, "previous_close": float | None }.
        Uses cache when entry is within TTL; otherwise fetches (with timeout). On timeout
        or per-symbol failure, returns current_price=None, display_name=symbol, previous_close=None.
        """
        if not symbols:
            return {}
        now = time.monotonic()
        result = {}
        to_fetch = []
        for sym in symbols:
            key = (sym or "").strip().upper()
            if not key:
                continue
            if key in self._cache:
                price, name, prev_close, cached_at = self._cache[key]
                if now - cached_at <= self._ttl:
                    result[key] = {"current_price": price, "display_name": name, "previous_close": prev_close}
                    continue
            to_fetch.append(key)

        if to_fetch:
            try:
                with ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(_fetch_quotes_impl, to_fetch)
                    fetched = fut.result(timeout=self._fetch_timeout)
            except (FuturesTimeoutError, Exception):
                fetched = {}
                for sym in to_fetch:
                    fetched[sym] = {"current_price": None, "display_name": sym, "previous_close": None}

            for sym in to_fetch:
                data = fetched.get(sym) or {"current_price": None, "display_name": sym, "previous_close": None}
                price = data.get("current_price")
                name = data.get("display_name") or sym
                prev_close = data.get("previous_close")
                result[sym] = {"current_price": price, "display_name": name, "previous_close": prev_close}
                self._cache[sym] = (price, name, prev_close, time.monotonic())

        return result
