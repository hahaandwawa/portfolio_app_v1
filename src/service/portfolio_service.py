"""
Portfolio service: compute portfolio summary (cash + positions) from transactions.
No persistence; all data derived from TransactionService.list_transactions.
Optionally enriches positions with quote data (price, name) and computed fields
(market_value, unrealized_pnl, weight_pct) via QuoteService.
"""

from collections import defaultdict
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from src.service.enums import TransactionType
from src.service.transaction_service import TransactionService

if TYPE_CHECKING:
    from src.service.quote_service import QuoteService


def _normalize_symbol(s: Optional[str]) -> Optional[str]:
    """Normalize symbol: strip and uppercase; empty/None -> None."""
    if s is None:
        return None
    t = (s or "").strip().upper()
    return t if t else None


def _round2(value: float) -> float:
    """Round to 2 decimal places for cash and total_cost."""
    return round(float(value), 2)


def _round_quantity(value: float) -> float:
    """Round quantity to 4 decimal places (fractional shares)."""
    return round(float(value), 4)


class PortfolioService:
    """Computes portfolio summary from transactions for given account(s)."""

    def __init__(
        self,
        transaction_service: Optional[TransactionService] = None,
        quote_service: Optional["QuoteService"] = None,
    ):
        self._txn_svc = transaction_service or TransactionService()
        self._quote_svc = quote_service

    def get_summary(
        self,
        account_names: Optional[list[str]] = None,
        include_quotes: bool = True,
    ) -> dict:
        """
        Return portfolio summary for the given account(s).

        - account_names: If None or empty, include all accounts (same as transaction list).
        - include_quotes: If True and quote_service is set, enrich positions with
          display_name, latest_price, cost_price, market_value, unrealized_pnl,
          unrealized_pnl_pct, weight_pct.
        - Returns: dict with "cash_balance", "account_cash", "positions".
          Positions are sorted by symbol; when include_quotes=True each position
          may include optional quote and computed fields (null when quote missing).
        """
        # Same semantics as list_transactions: None or empty list => all accounts
        rows = self._txn_svc.list_transactions(account_names=account_names)

        cash = Decimal("0")
        # Per-account cash (for account_cash in response)
        by_account: dict[str, Decimal] = defaultdict(Decimal)
        # Per-symbol: quantity_held, total_buy_cost, total_buy_qty (for avg cost)
        by_symbol: dict[str, dict] = defaultdict(
            lambda: {"quantity": Decimal("0"), "total_buy_cost": Decimal("0"), "total_buy_qty": Decimal("0")}
        )

        for row in rows:
            acc_name = row.get("account_name") or ""
            txn_type_str = row.get("txn_type")
            try:
                txn_type = TransactionType(txn_type_str)
            except (ValueError, TypeError):
                continue

            fees = Decimal(str(row.get("fees") or 0))

            if txn_type == TransactionType.CASH_DEPOSIT:
                amt = row.get("cash_amount")
                if amt is not None:
                    val = Decimal(str(amt))
                    cash += val
                    by_account[acc_name] += val

            elif txn_type == TransactionType.CASH_WITHDRAW:
                amt = row.get("cash_amount")
                if amt is not None:
                    val = Decimal(str(amt))
                    cash -= val
                    by_account[acc_name] -= val

            elif txn_type == TransactionType.BUY:
                qty = row.get("quantity")
                price = row.get("price")
                if qty is not None and price is not None:
                    amount = Decimal(str(qty)) * Decimal(str(price))
                else:
                    amount = Decimal("0")
                debit = amount + fees
                cash -= debit
                by_account[acc_name] -= debit
                sym = _normalize_symbol(row.get("symbol"))
                if sym:
                    by_symbol[sym]["quantity"] += Decimal(str(qty or 0))
                    by_symbol[sym]["total_buy_cost"] += amount + fees
                    by_symbol[sym]["total_buy_qty"] += Decimal(str(qty or 0))

            elif txn_type == TransactionType.SELL:
                qty = row.get("quantity")
                price = row.get("price")
                if qty is not None and price is not None:
                    amount = Decimal(str(qty)) * Decimal(str(price))
                else:
                    amount = Decimal("0")
                credit = amount - fees
                cash += credit
                cash_dest = row.get("cash_destination_account") or acc_name
                by_account[cash_dest] += credit
                sym = _normalize_symbol(row.get("symbol"))
                if sym:
                    by_symbol[sym]["quantity"] -= Decimal(str(qty or 0))

        # Build positions: only quantity > 0, total_cost = quantity_held * avg_cost
        positions = []
        for sym, data in sorted(by_symbol.items()):
            qty_held = data["quantity"]
            if qty_held <= 0:
                continue
            total_buy_cost = data["total_buy_cost"]
            total_buy_qty = data["total_buy_qty"]
            if total_buy_qty and total_buy_qty > 0:
                avg_cost = total_buy_cost / total_buy_qty
                total_cost = _round2(float(qty_held * avg_cost))
            else:
                total_cost = 0.0
            cost_price = (total_cost / float(qty_held)) if qty_held else 0.0
            positions.append({
                "symbol": sym,
                "quantity": _round_quantity(float(qty_held)),
                "total_cost": total_cost,
                "cost_price": _round2(float(cost_price)),
            })

        # account_cash: for filtered set only (when account_names given, those; when not, all in rows)
        account_cash = [
            {"account_name": name, "cash_balance": _round2(float(bal))}
            for name, bal in sorted(by_account.items())
        ]

        if include_quotes and self._quote_svc and positions:
            positions = self._enrich_positions_with_quotes(positions)

        return {
            "cash_balance": _round2(float(cash)),
            "account_cash": account_cash,
            "positions": positions,
        }

    def get_quantity_held(self, account_name: str, symbol: str) -> Decimal:
        """
        Return the quantity of symbol held in the given account (from transactions).
        Returns Decimal(0) if the account has no position in that symbol.
        """
        summary = self.get_summary(account_names=[account_name], include_quotes=False)
        norm = _normalize_symbol(symbol)
        if not norm:
            return Decimal("0")
        for pos in summary["positions"]:
            if pos["symbol"] == norm:
                return Decimal(str(pos["quantity"]))
        return Decimal("0")

    def get_positions_by_symbol(self, symbol: str) -> list[dict]:
        """
        Return per-account quantities for the given symbol (only accounts with quantity > 0),
        sorted by quantity descending. Each item: {"account_name": str, "quantity": float}.
        """
        norm = _normalize_symbol(symbol)
        if not norm:
            return []
        rows = self._txn_svc.list_transactions(account_names=None)
        accounts = set(r.get("account_name") or "" for r in rows)
        result = []
        for acc in accounts:
            if not acc:
                continue
            qty = self.get_quantity_held(acc, norm)
            if qty > 0:
                result.append({
                    "account_name": acc,
                    "quantity": _round_quantity(float(qty)),
                })
        result.sort(key=lambda x: -x["quantity"])
        return result

    def _enrich_positions_with_quotes(self, positions: list[dict]) -> list[dict]:
        """Attach quote and computed fields to each position. Mutates and returns positions."""
        symbols = [p["symbol"] for p in positions]
        quotes = self._quote_svc.get_quotes(symbols)

        total_market_value = 0.0
        for p in positions:
            sym = p["symbol"]
            qty = p["quantity"]
            total_cost = p["total_cost"]
            # cost_price already set in base positions

            q = quotes.get(sym) or {}
            price = q.get("current_price")
            p["display_name"] = q.get("display_name") or sym
            p["latest_price"] = _round2(price) if price is not None else None

            if price is not None and qty is not None:
                market_value = _round2(float(qty) * float(price))
                p["market_value"] = market_value
                total_market_value += market_value
                p["unrealized_pnl"] = _round2(market_value - total_cost)
                p["unrealized_pnl_pct"] = (
                    _round2((market_value - total_cost) / total_cost * 100) if total_cost else None
                )
            else:
                p["market_value"] = None
                p["unrealized_pnl"] = None
                p["unrealized_pnl_pct"] = None

        for p in positions:
            mv = p.get("market_value")
            if mv is not None and total_market_value and total_market_value > 0:
                p["weight_pct"] = _round2(mv / total_market_value * 100)
            else:
                p["weight_pct"] = None

        return positions
