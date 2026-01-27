"""Pydantic schemas for account endpoints."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.models.enums import CostBasisMethod


class AccountCreate(BaseModel):
    """Request schema for creating an account."""

    name: str = Field(..., min_length=1, max_length=255, description="Unique account name")
    cost_basis_method: CostBasisMethod = Field(
        default=CostBasisMethod.FIFO,
        description="Cost basis calculation method",
    )


class AccountResponse(BaseModel):
    """Response schema for a single account."""

    model_config = {"from_attributes": True}

    account_id: str
    name: str
    cost_basis_method: CostBasisMethod
    created_at_est: Optional[datetime] = None


class AccountListResponse(BaseModel):
    """Response schema for listing accounts."""

    accounts: list[AccountResponse]
    count: int
