"""
Net value curve service: compute baseline (Holdings Cost) and market value over time.
Day-by-day incremental holdings with correct avg-cost mechanics (§1.1.1).
V1: baseline = Holdings Cost (avg); transactions on date T applied before T's close value.
"""

from collections import defaultdict
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from src.service.enums import TransactionType
from src.service.transaction_service import TransactionService
from src.service.historical_price_service import HistoricalPriceService
from src.service.util import normalize_symbol, round2


def _parse_date(s) -> date:
    if isinstance(s, date):
        return s
    if isinstance(s, datetime):
        return s.date()
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()


def _date_str(d: date) -> str:
    return d.isoformat()


class NetValueService:
    """
    Computes net value curve: baseline (Holdings Cost) and market value per calendar day.
    Uses HistoricalPriceService for close prices; forward-fills non-trading days.
    """

    def __init__(
        self,
        transaction_service: TransactionService,
        historical_price_service: HistoricalPriceService,
    ):
        self._txn_svc = transaction_service
        self._price_svc = historical_price_service

    def get_net_value_curve(
        self,
        account_names: Optional[list[str]] = None,
        start_date: Optional[datetime | date] = None,
        end_date: Optional[datetime | date] = None,
        include_cash: bool = True,
        refresh_prices: bool = False,
    ) -> dict:
        """
        Returns columnar arrays for the net value curve.
        - baseline: Holdings Cost (v1) = sum over positions of (avg_cost × shares).
        - market_value: sum(shares × close) + (cash if include_cash).
        - profit_loss = market_value - baseline; profit_loss_pct = (profit_loss / baseline) * 100 when baseline > 0 else null.
        - is_trading_day: false for weekends/holidays.
        - last_trading_date: actual last trading date whose close was used (for tooltip).
        """
        rows = self._txn_svc.list_transactions(account_names=account_names)
        # Ascending by time for day-by-day application
        rows_asc = sorted(rows, key=lambda r: r.get("txn_time_est") or "")
        if not rows_asc:
            return self._empty_response(include_cash)

        # Trade date: US/Eastern calendar date (v1: use txn_time_est date as-is)
        def trade_date(r):
            t = r.get("txn_time_est")
            if not t:
                return None
            return _parse_date(t)

        txn_by_date: dict[str, list[dict]] = defaultdict(list)
        for r in rows_asc:
            d = trade_date(r)
            if d is not None:
                txn_by_date[_date_str(d)].append(r)

        all_dates = sorted(txn_by_date.keys())
        if not all_dates:
            return self._empty_response(include_cash)

        first_txn_date = _parse_date(all_dates[0])
        last_txn_date = _parse_date(all_dates[-1])
        start = _parse_date(start_date) if start_date else first_txn_date
        end = _parse_date(end_date) if end_date else max(
            last_txn_date,
            date.today(),
        )
        if start > end:
            return self._empty_response(include_cash)

        # Symbols that ever have nonzero shares in [start, end]
        symbols_in_range = self._symbols_in_range(txn_by_date, start, end)
        if not symbols_in_range:
            # Cash-only: still produce curve for cash
            pass

        # Fetch prices for all calendar days (forward-filled)
        price_series = self._price_svc.get_historical_prices(
            list(symbols_in_range) if symbols_in_range else [],
            start,
            end,
            refresh=refresh_prices,
        )

        # Day-by-day state: holdings[symbol] = {"shares": float, "avg_cost": float}, cash = float
        holdings: dict[str, dict] = defaultdict(lambda: {"shares": 0.0, "avg_cost": 0.0})
        cash = 0.0

        dates_out = []
        baseline_out = []
        market_value_out = []
        profit_loss_out = []
        profit_loss_pct_out = []
        is_trading_day_out = []
        last_trading_date_out = []

        d = start
        while d <= end:
            date_s = _date_str(d)
            # Apply all transactions on this date (before close value)
            for r in txn_by_date.get(date_s, []):
                self._apply_transaction(r, holdings)

            # Recompute cash up to and including this day (in case we applied txns)
            cash = self._cash_at_date(txn_by_date, start, d)
            # Stock cost and market value (holdings only)
            stock_cost = sum(
                h["shares"] * h["avg_cost"] for h in holdings.values() if h["shares"] != 0
            )
            stock_mv = 0.0
            for sym, h in holdings.items():
                if h["shares"] == 0:
                    continue
                series = price_series.get(sym) or []
                # Find close and last_trading_date for this calendar day
                close_val = None
                last_trading = date_s
                for pt in series:
                    if pt["date"] == date_s:
                        close_val = pt.get("close")
                        last_trading = pt.get("last_trading_date") or date_s
                        break
                if close_val is not None:
                    stock_mv += h["shares"] * close_val
            
            # Baseline and market value: include cash when include_cash=true
            if include_cash:
                baseline = cash + stock_cost
                mv = cash + stock_mv
            else:
                baseline = stock_cost
                mv = stock_mv

            # is_trading_day: true iff we have a real close for this date (not forward-filled)
            # From price data: if last_trading_date == date_s then it's a trading day
            any_trading = False
            last_trading_used = date_s
            for sym in holdings:
                if holdings[sym]["shares"] == 0:
                    continue
                series = price_series.get(sym) or []
                for pt in series:
                    if pt["date"] == date_s:
                        if pt.get("last_trading_date") == date_s:
                            any_trading = True
                        last_trading_used = pt.get("last_trading_date") or date_s
                        break
            # If no positions, use calendar weekday (rough proxy)
            if not any(holdings[s]["shares"] != 0 for s in holdings):
                any_trading = d.weekday() < 5  # Mon–Fri
                last_trading_used = date_s

            dates_out.append(date_s)
            baseline_out.append(round2(baseline))
            market_value_out.append(round2(mv))
            pl = round2(mv - baseline)
            profit_loss_out.append(pl)
            if baseline > 0:
                profit_loss_pct_out.append(round2(pl / baseline * 100))
            else:
                profit_loss_pct_out.append(None)
            is_trading_day_out.append(any_trading)
            last_trading_date_out.append(last_trading_used)

            d += timedelta(days=1)

        baseline_label = (
            "Book Value (cash + holdings cost)" if include_cash else "Holdings Cost (avg)"
        )
        return {
            "baseline_label": baseline_label,
            "price_type": "close",
            "includes_cash": include_cash,
            "dates": dates_out,
            "baseline": baseline_out,
            "market_value": market_value_out,
            "profit_loss": profit_loss_out,
            "profit_loss_pct": profit_loss_pct_out,
            "is_trading_day": is_trading_day_out,
            "last_trading_date": last_trading_date_out,
        }

    def _empty_response(self, include_cash: bool) -> dict:
        baseline_label = (
            "Book Value (cash + holdings cost)" if include_cash else "Holdings Cost (avg)"
        )
        return {
            "baseline_label": baseline_label,
            "price_type": "close",
            "includes_cash": include_cash,
            "dates": [],
            "baseline": [],
            "market_value": [],
            "profit_loss": [],
            "profit_loss_pct": [],
            "is_trading_day": [],
            "last_trading_date": [],
        }

    def _symbols_in_range(
        self,
        txn_by_date: dict[str, list[dict]],
        start: date,
        end: date,
    ) -> set[str]:
        symbols = set()
        d = start
        while d <= end:
            for r in txn_by_date.get(_date_str(d), []):
                t = r.get("txn_type")
                if t in (TransactionType.BUY.value, TransactionType.SELL.value):
                    sym = normalize_symbol(r.get("symbol"))
                    if sym:
                        symbols.add(sym)
            d += timedelta(days=1)
        return symbols

    def _apply_transaction(self, r: dict, holdings: dict) -> None:
        """Apply one transaction to holdings (avg-cost mechanics). Cash is computed separately."""
        t = r.get("txn_type")
        try:
            txn_type = TransactionType(t)
        except (ValueError, TypeError):
            return
        acc = r.get("account_name") or ""
        fees = float(r.get("fees") or 0)
        sym = normalize_symbol(r.get("symbol"))

        if txn_type == TransactionType.BUY and sym:
            qty = float(r.get("quantity") or 0)
            price = float(r.get("price") or 0)
            if qty <= 0:
                return
            prev = holdings[sym]
            prev_shares = prev["shares"]
            prev_avg = prev["avg_cost"]
            cost = qty * price + fees
            if prev_shares + qty == 0:
                new_avg = 0.0
            else:
                new_avg = (prev_shares * prev_avg + cost) / (prev_shares + qty)
            holdings[sym] = {"shares": prev_shares + qty, "avg_cost": new_avg}

        elif txn_type == TransactionType.SELL and sym:
            qty = float(r.get("quantity") or 0)
            if qty <= 0:
                return
            prev = holdings[sym]
            new_shares = prev["shares"] - qty
            if new_shares <= 0:
                new_shares = 0.0
                new_avg = 0.0
            else:
                new_avg = prev["avg_cost"]
            holdings[sym] = {"shares": new_shares, "avg_cost": new_avg}

    def _cash_at_date(
        self,
        txn_by_date: dict[str, list[dict]],
        range_start: date,
        as_of: date,
    ) -> float:
        """Cash balance after applying all transactions from range_start through as_of (inclusive)."""
        cash = 0.0
        d = range_start
        while d <= as_of:
            for r in txn_by_date.get(_date_str(d), []):
                t = r.get("txn_type")
                try:
                    txn_type = TransactionType(t)
                except (ValueError, TypeError):
                    continue
                fees = float(r.get("fees") or 0)
                if txn_type == TransactionType.CASH_DEPOSIT:
                    amt = r.get("cash_amount")
                    if amt is not None:
                        cash += float(amt)
                elif txn_type == TransactionType.CASH_WITHDRAW:
                    amt = r.get("cash_amount")
                    if amt is not None:
                        cash -= float(amt)
                elif txn_type == TransactionType.BUY:
                    qty = r.get("quantity")
                    price = r.get("price")
                    if qty is not None and price is not None:
                        cash -= float(qty) * float(price) + fees
                elif txn_type == TransactionType.SELL:
                    qty = r.get("quantity")
                    price = r.get("price")
                    if qty is not None and price is not None:
                        cash += float(qty) * float(price) - fees
            d += timedelta(days=1)
        return round2(cash)
