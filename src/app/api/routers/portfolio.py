"""Portfolio summary API: GET /portfolio from transaction-derived data."""

from typing import Optional

from fastapi import APIRouter, Query

from src.service.portfolio_service import PortfolioService
from src.service.quote_service import QuoteService
from src.app.api.schemas.portfolio import (
    PortfolioSummary,
    PortfolioPosition,
    AccountCash,
    PositionsBySymbolResponse,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

_quote_service: Optional[QuoteService] = None
_portfolio_service: Optional[PortfolioService] = None


def _get_quote_service() -> QuoteService:
    global _quote_service
    if _quote_service is None:
        _quote_service = QuoteService()
    return _quote_service


def _get_portfolio_service() -> PortfolioService:
    global _portfolio_service
    if _portfolio_service is None:
        _portfolio_service = PortfolioService(quote_service=_get_quote_service())
    return _portfolio_service


@router.get("", response_model=PortfolioSummary)
def get_portfolio(
    account: Optional[list[str]] = Query(None, alias="account"),
    quotes: bool = Query(True, description="Include quote data and computed fields (latest_price, market_value, etc.). Set to 0 for lightweight response."),
):
    """
    Return portfolio summary for the given account(s).

    - account: Optional repeatable query param. If omitted or empty, include all accounts.
    - quotes: If true (default), fetch Yahoo quotes and include display_name, latest_price,
      cost_price, market_value, unrealized_pnl, unrealized_pnl_pct, weight_pct per position.
      If false, positions contain only symbol, quantity, total_cost.
    - Response: cash_balance, account_cash, positions (enriched when quotes=true).
    """
    svc = _get_portfolio_service()
    account_names = account if account else None
    raw = svc.get_summary(account_names=account_names, include_quotes=quotes)
    return PortfolioSummary(
        cash_balance=raw["cash_balance"],
        account_cash=[AccountCash(**a) for a in raw["account_cash"]],
        positions=[PortfolioPosition(**p) for p in raw["positions"]],
    )


@router.get("/positions-by-symbol", response_model=PositionsBySymbolResponse)
def get_positions_by_symbol(
    symbol: str = Query(..., description="Stock symbol (e.g. AAPL)"),
):
    """
    Return per-account quantities for the given symbol (only accounts with quantity > 0),
    sorted by quantity descending. Used to default source/cash-destination for SELL.
    """
    if not (symbol or "").strip():
        return PositionsBySymbolResponse(symbol=(symbol or "").strip().upper(), positions=[])
    svc = _get_portfolio_service()
    raw = svc.get_positions_by_symbol(symbol.strip().upper())
    return PositionsBySymbolResponse(
        symbol=symbol.strip().upper(),
        positions=[{"account_name": p["account_name"], "quantity": p["quantity"]} for p in raw],
    )
