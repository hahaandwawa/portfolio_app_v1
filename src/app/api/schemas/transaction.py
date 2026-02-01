from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    account_name: str
    txn_type: str  # BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAW
    txn_time_est: datetime
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    cash_amount: Optional[float] = None
    fees: float = 0.0
    note: Optional[str] = None


class TransactionEdit(BaseModel):
    account_name: Optional[str] = None
    txn_type: Optional[str] = None
    txn_time_est: Optional[datetime] = None
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    cash_amount: Optional[float] = None
    fees: Optional[float] = None
    note: Optional[str] = None


class TransactionOut(BaseModel):
    txn_id: str
    account_name: str
    txn_type: str
    txn_time_est: str
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    cash_amount: Optional[float] = None
    amount: Optional[float] = None  # qty*price for BUY/SELL, else cash_amount
    fees: float = 0.0
    note: Optional[str] = None


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int
    total_pages: int
