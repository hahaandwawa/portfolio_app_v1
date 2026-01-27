"""Portfolio analysis endpoints."""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_portfolio_engine,
    get_analysis_service,
    get_market_data_service,
)
from app.api.schemas import (
    PositionResponse,
    PositionsResponse,
    CashBalanceResponse,
    TodayPnlResponse,
    AllocationItemResponse,
    AllocationResponse,
    QuoteResponse,
)
from app.services import PortfolioEngine, AnalysisService, MarketDataService

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/positions", response_model=PositionsResponse)
def get_positions(
    account_ids: Optional[str] = Query(None, description="Comma-separated account IDs (all if empty)"),
    portfolio: PortfolioEngine = Depends(get_portfolio_engine),
    analysis: AnalysisService = Depends(get_analysis_service),
) -> PositionsResponse:
    """Get current holdings with market prices."""
    # Parse account IDs
    if account_ids:
        account_id_list = account_ids.split(",")
    else:
        # TODO: Get all account IDs from ledger service
        account_id_list = []

    positions = analysis.get_positions_with_prices(account_id_list)
    cash_balance = portfolio.aggregate_cash(account_id_list) if account_id_list else Decimal("0")

    total_value = cash_balance
    for p in positions:
        if p.market_value:
            total_value += p.market_value

    return PositionsResponse(
        positions=[
            PositionResponse(
                symbol=p.symbol,
                shares=p.shares,
                last_price=p.last_price,
                market_value=p.market_value,
                prev_close=p.prev_close,
            )
            for p in positions
        ],
        cash_balance=cash_balance,
        total_value=total_value,
    )


@router.get("/cash", response_model=CashBalanceResponse)
def get_cash_balance(
    account_ids: Optional[str] = Query(None, description="Comma-separated account IDs"),
    portfolio: PortfolioEngine = Depends(get_portfolio_engine),
) -> CashBalanceResponse:
    """Get aggregated cash balance."""
    if account_ids:
        account_id_list = account_ids.split(",")
        cash = portfolio.aggregate_cash(account_id_list)
    else:
        cash = Decimal("0")

    return CashBalanceResponse(cash_balance=cash)


@router.get("/pnl", response_model=TodayPnlResponse)
def get_today_pnl(
    account_ids: Optional[str] = Query(None, description="Comma-separated account IDs"),
    analysis: AnalysisService = Depends(get_analysis_service),
) -> TodayPnlResponse:
    """Calculate today's P/L for given accounts."""
    account_id_list = account_ids.split(",") if account_ids else []

    pnl = analysis.today_pnl(account_id_list)

    return TodayPnlResponse(
        pnl_dollars=pnl.pnl_dollars,
        pnl_percent=pnl.pnl_percent,
        prev_close_value=pnl.prev_close_value,
        current_value=pnl.current_value,
        as_of=pnl.as_of,
    )


@router.get("/allocation", response_model=AllocationResponse)
def get_allocation(
    account_ids: Optional[str] = Query(None, description="Comma-separated account IDs"),
    analysis: AnalysisService = Depends(get_analysis_service),
) -> AllocationResponse:
    """Get portfolio allocation breakdown."""
    account_id_list = account_ids.split(",") if account_ids else []

    allocation = analysis.allocation(account_id_list)

    return AllocationResponse(
        items=[
            AllocationItemResponse(
                symbol=item.symbol,
                market_value=item.market_value,
                percentage=item.percentage,
            )
            for item in allocation.items
        ],
        total_value=allocation.total_value,
        as_of=allocation.as_of,
    )


@router.get("/quotes", response_model=list[QuoteResponse])
def get_quotes(
    symbols: str = Query(..., description="Comma-separated symbols"),
    market: MarketDataService = Depends(get_market_data_service),
) -> list[QuoteResponse]:
    """Get market quotes for symbols."""
    symbol_list = [s.strip().upper() for s in symbols.split(",")]
    quotes = market.get_quotes(symbol_list)

    return [
        QuoteResponse(
            symbol=q.symbol,
            last_price=q.last_price,
            prev_close=q.prev_close,
            as_of=q.as_of,
        )
        for q in quotes.values()
    ]
