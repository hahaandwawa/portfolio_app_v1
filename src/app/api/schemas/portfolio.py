"""Pydantic schemas for portfolio summary API."""

from typing import Optional

from pydantic import BaseModel


class PortfolioPosition(BaseModel):
    """A single position: symbol, quantity, total cost; optional quote and computed fields."""

    symbol: str
    quantity: float
    total_cost: float
    # Quote and computed fields (present when quotes=1; null when quote missing or quotes=0)
    display_name: Optional[str] = None
    latest_price: Optional[float] = None
    cost_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    weight_pct: Optional[float] = None


class AccountCash(BaseModel):
    """Per-account cash balance for badge display."""

    account_name: str
    cash_balance: float


class PortfolioSummary(BaseModel):
    """Portfolio summary: cash balance, per-account cash, and positions (quantity > 0)."""

    cash_balance: float
    account_cash: list[AccountCash]
    positions: list[PortfolioPosition]


class PositionByAccount(BaseModel):
    """Per-account position for a symbol (for positions-by-symbol endpoint)."""

    account_name: str
    quantity: float


class PositionsBySymbolResponse(BaseModel):
    """Response for GET /portfolio/positions-by-symbol."""

    symbol: str
    positions: list[PositionByAccount]
