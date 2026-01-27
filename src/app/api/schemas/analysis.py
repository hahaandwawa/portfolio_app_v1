"""Pydantic schemas for analysis endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class PositionResponse(BaseModel):
    """Response schema for a single position."""

    symbol: str
    shares: Decimal
    last_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    prev_close: Optional[Decimal] = None


class PositionsResponse(BaseModel):
    """Response schema for positions listing."""

    positions: list[PositionResponse]
    cash_balance: Decimal
    total_value: Decimal


class CashBalanceResponse(BaseModel):
    """Response schema for cash balance."""

    cash_balance: Decimal


class TodayPnlResponse(BaseModel):
    """Response schema for today's P/L calculation."""

    pnl_dollars: Decimal
    pnl_percent: Optional[Decimal] = None
    prev_close_value: Decimal
    current_value: Decimal
    as_of: Optional[datetime] = None


class AllocationItemResponse(BaseModel):
    """Response schema for a single allocation item."""

    symbol: str
    market_value: Decimal
    percentage: Decimal


class AllocationResponse(BaseModel):
    """Response schema for allocation breakdown."""

    items: list[AllocationItemResponse]
    total_value: Decimal
    as_of: Optional[datetime] = None


class QuoteResponse(BaseModel):
    """Response schema for a market quote."""

    symbol: str
    last_price: Decimal
    prev_close: Decimal
    as_of: datetime
