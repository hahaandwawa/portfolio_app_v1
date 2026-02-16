"""
Historical price service: fetch and cache daily close prices for net value curve.
Uses SQLite (symbol, date) cache; fetches from yfinance when missing.
Forward-fills weekends/holidays with previous trading day's close.
V1 uses Close (unadjusted) for market value; price_type = 'close'.
"""

from datetime import datetime, date, timedelta, timezone
from typing import Optional

import sqlite3

from src.service.util import _load_config, round2


def _get_yf():
    import yfinance as yf
    return yf


def _date_str(d: date) -> str:
    return d.isoformat()


def _parse_date(s: str) -> date:
    if isinstance(s, date):
        return s
    if isinstance(s, datetime):
        return s.date()
    return datetime.fromisoformat(s.replace("Z", "+00:00")).date()


class HistoricalPriceService:
    """
    Fetches historical close prices from yfinance, caches by (symbol, date) in SQLite.
    Does not invalidate cache on transaction changes.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is not None:
            self._db_path = db_path
        else:
            config = _load_config()
            self._db_path = config.get(
                "HistoricalPricesDBPath", "./data/historical_prices.sqlite"
            )

    def get_historical_prices(
        self,
        symbols: list[str],
        start_date: datetime | date,
        end_date: datetime | date,
        refresh: bool = False,
    ) -> dict[str, list[dict]]:
        """
        Returns for each symbol a list of daily points from start_date to end_date (calendar days).
        Each point: {"date": "YYYY-MM-DD", "close": float, "last_trading_date": "YYYY-MM-DD"}.
        Non-trading days are forward-filled; last_trading_date is the actual trading date whose close was used.
        """
        start = _parse_date(start_date)
        end = _parse_date(end_date)
        if start > end:
            return {s: [] for s in symbols}

        norm_symbols = [s.strip().upper() for s in symbols if (s or "").strip()]
        if not norm_symbols:
            return {}

        # Load from cache (and optionally overwrite with refresh)
        cache = self._load_from_db(norm_symbols, start, end, overwrite=refresh)

        # Fetch missing from yfinance (batch then retry failed)
        missing = self._missing_ranges(cache, norm_symbols, start, end)
        if missing:
            fetched = self._fetch_from_yfinance(missing)
            self._merge_and_persist(cache, fetched, start, end)

        # Build calendar-day series with forward-fill and last_trading_date
        result = {}
        for sym in norm_symbols:
            result[sym] = self._build_series_with_forward_fill(
                cache.get(sym) or {}, start, end
            )
        return result

    def get_price_on_date(
        self,
        symbol: str,
        target_date: datetime | date,
    ) -> Optional[float]:
        """
        Get close price for symbol on target_date.
        If market holiday/weekend, returns previous trading day's close (forward-fill).
        """
        sym = (symbol or "").strip().upper()
        if not sym:
            return None
        t = _parse_date(target_date)
        # Request a short range so we can forward-fill from previous trading days
        from datetime import timedelta
        start = t - timedelta(days=14)
        data = self.get_historical_prices([sym], start, t)
        series = data.get(sym) or []
        if not series:
            return None
        # Series is ordered by date; last point is target_date (possibly forward-filled)
        return series[-1].get("close") if series else None

    def _load_from_db(
        self,
        symbols: list[str],
        start: date,
        end: date,
        overwrite: bool = False,
    ) -> dict[str, dict[str, float]]:
        """Load cached close_price by (symbol, date). Returns {symbol: {date_str: close}}."""
        conn = sqlite3.connect(self._db_path)
        out = {s: {} for s in symbols}
        try:
            cur = conn.cursor()
            start_s = _date_str(start)
            end_s = _date_str(end)
            for sym in symbols:
                cur.execute(
                    """SELECT date, close_price FROM historical_prices
                       WHERE symbol = ? AND date >= ? AND date <= ?""",
                    (sym, start_s, end_s),
                )
                for row in cur.fetchall():
                    out[sym][row[0]] = row[1]
        finally:
            conn.close()
        return out

    def _missing_ranges(
        self,
        cache: dict[str, dict[str, float]],
        symbols: list[str],
        start: date,
        end: date,
    ) -> dict[str, list[tuple[date, date]]]:
        """For each symbol, list of (range_start, range_end) of calendar days missing in cache."""
        missing = {}
        d = start
        while d <= end:
            date_s = _date_str(d)
            for sym in symbols:
                if cache.get(sym, {}).get(date_s) is None:
                    if sym not in missing:
                        missing[sym] = []
                    # coalesce contiguous missing days into one range
                    if missing[sym] and missing[sym][-1][1] == d - timedelta(days=1):
                        missing[sym][-1] = (missing[sym][-1][0], d)
                    else:
                        missing[sym].append((d, d))
            d += timedelta(days=1)
        # coalesce adjacent ranges
        for sym in list(missing.keys()):
            merged = []
            for a, b in sorted(missing[sym]):
                if merged and (a - merged[-1][1]).days <= 1:
                    merged[-1] = (merged[-1][0], b)
                else:
                    merged.append((a, b))
            missing[sym] = merged
        return missing

    def _fetch_from_yfinance(
        self,
        missing: dict[str, list[tuple[date, date]]],
    ) -> dict[str, dict[str, float]]:
        """
        Fetch missing (symbol, date) from yfinance. Batch download then retry failed per ticker.
        Returns {symbol: {date_str: close}}.
        """
        yf = _get_yf()
        result = {sym: {} for sym in missing}
        symbols_to_fetch = list(missing.keys())
        if not symbols_to_fetch:
            return result

        all_starts = [r[0][0] for r in missing.values()]
        all_ends = [r[-1][1] for r in missing.values()]
        batch_start = min(all_starts)
        batch_end = max(all_ends)

        # Batch download
        try:
            df = yf.download(
                symbols_to_fetch,
                start=batch_start,
                end=batch_end + timedelta(days=1),
                group_by="ticker",
                progress=False,
                auto_adjust=False,
                threads=False,
            )
        except Exception:
            df = None

        if df is not None and not df.empty:
            self._parse_batch_df(df, symbols_to_fetch, result)

        # Retry symbols that have no data
        for sym in symbols_to_fetch:
            if result[sym]:
                continue
            for r_start, r_end in missing[sym]:
                try:
                    ticker = yf.Ticker(sym)
                    hist = ticker.history(
                        start=r_start,
                        end=r_end + timedelta(days=1),
                        auto_adjust=False,
                    )
                    if hist is not None and not hist.empty:
                        for idx, row in hist.iterrows():
                            dt = idx.date() if hasattr(idx, "date") else idx
                            close = row.get("Close", None)
                            if close is not None and not (
                                isinstance(close, float) and close != close
                            ):
                                result[sym][_date_str(dt)] = round2(float(close))
                except Exception:
                    pass
        return result

    def _parse_batch_df(
        self,
        df,
        symbols: list[str],
        result: dict[str, dict[str, float]],
    ) -> None:
        """Parse yfinance download DataFrame into result (mutates result)."""
        import pandas as pd

        if len(symbols) == 1:
            sym = symbols[0]
            if "Close" in df.columns:
                for idx, row in df.iterrows():
                    dt = idx.date() if hasattr(idx, "date") else idx
                    close = row.get("Close")
                    if close is not None and not (
                        isinstance(close, float) and close != close
                    ):
                        result[sym][_date_str(dt)] = round2(float(close))
            return

        # Multi-ticker: columns are (Ticker, OHLC) when group_by='ticker'
        for sym in symbols:
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    if (sym, "Close") in df.columns:
                        series = df[(sym, "Close")]
                    else:
                        series = df[sym]["Close"] if sym in df.columns else None
                else:
                    series = df["Close"] if sym == symbols[0] else None
                if series is not None:
                    for idx, val in series.items():
                        dt = idx.date() if hasattr(idx, "date") else idx
                        if val is not None and not (
                            isinstance(val, float) and val != val
                        ):
                            result[sym][_date_str(dt)] = round2(float(val))
            except Exception:
                pass

    def _merge_and_persist(
        self,
        cache: dict[str, dict[str, float]],
        fetched: dict[str, dict[str, float]],
        start: date,
        end: date,
    ) -> None:
        """Merge fetched into cache and write to DB."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        conn = sqlite3.connect(self._db_path)
        try:
            for sym, by_date in fetched.items():
                for date_s, close in by_date.items():
                    cache.setdefault(sym, {})[date_s] = close
                    conn.execute(
                        """INSERT OR REPLACE INTO historical_prices
                           (symbol, date, close_price, price_type, updated_at)
                           VALUES (?, ?, ?, 'close', ?)""",
                        (sym, date_s, close, now),
                    )
            conn.commit()
        finally:
            conn.close()

    def _build_series_with_forward_fill(
        self,
        by_date: dict[str, float],
        start: date,
        end: date,
    ) -> list[dict]:
        """
        Build list of {date, close, last_trading_date} for every calendar day from start to end.
        Forward-fill close; last_trading_date is the date whose close we're using.
        """
        out = []
        last_close = None
        last_trading_date_s = None
        d = start
        while d <= end:
            date_s = _date_str(d)
            if date_s in by_date and by_date[date_s] is not None:
                last_close = by_date[date_s]
                last_trading_date_s = date_s
            out.append({
                "date": date_s,
                "close": last_close,
                "last_trading_date": last_trading_date_s or date_s,
            })
            d += timedelta(days=1)
        return out
