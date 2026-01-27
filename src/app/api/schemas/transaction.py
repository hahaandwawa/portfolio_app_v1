"""Pydantic schemas for transaction endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.domain.models.enums import TransactionType


class TransactionCreateRequest(BaseModel):
    """Request schema for creating a transaction."""

    account_id: str = Field(..., description="Account ID")
    txn_type: TransactionType = Field(..., description="Transaction type")
    txn_time_est: Optional[datetime] = Field(
        default=None,
        description="Transaction time (US/Eastern); defaults to now",
    )
    symbol: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Stock symbol (required for BUY/SELL)",
    )
    quantity: Optional[Decimal] = Field(
        default=None,
        gt=0,
        description="Number of shares (required for BUY/SELL)",
    )
    price: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Price per share (required for BUY/SELL)",
    )
    cash_amount: Optional[Decimal] = Field(
        default=None,
        gt=0,
        description="Cash amount (required for CASH_DEPOSIT/CASH_WITHDRAW)",
    )
    fees: Decimal = Field(default=Decimal("0"), ge=0, description="Transaction fees")
    note: Optional[str] = Field(default=None, max_length=500, description="Optional note")

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else None


class TransactionUpdateRequest(BaseModel):
    """Request schema for updating a transaction (partial update)."""

    txn_time_est: Optional[datetime] = None
    symbol: Optional[str] = Field(default=None, max_length=20)
    quantity: Optional[Decimal] = Field(default=None, gt=0)
    price: Optional[Decimal] = Field(default=None, ge=0)
    cash_amount: Optional[Decimal] = Field(default=None, gt=0)
    fees: Optional[Decimal] = Field(default=None, ge=0)
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else None


class TransactionResponse(BaseModel):
    """Response schema for a single transaction."""

    model_config = {"from_attributes": True}

    txn_id: str
    account_id: str
    txn_time_est: datetime
    txn_type: TransactionType
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    cash_amount: Optional[Decimal] = None
    fees: Decimal
    note: Optional[str] = None
    is_deleted: bool
    created_at_est: Optional[datetime] = None
    updated_at_est: Optional[datetime] = None


class TransactionListResponse(BaseModel):
    """Response schema for listing transactions."""

    transactions: list[TransactionResponse]
    count: int


class ImportSummaryResponse(BaseModel):
    """Response schema for CSV import results."""

    imported_count: int
    skipped_count: int
    error_count: int
    errors: list[str]
    import_batch_id: Optional[str] = None
