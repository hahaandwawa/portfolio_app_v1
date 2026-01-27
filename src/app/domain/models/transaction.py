"""Transaction and TransactionRevision domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.domain.models.enums import TransactionType, RevisionAction


@dataclass
class Transaction:
    """
    Ledger transaction entry (source of truth).

    Supports: BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAW.
    - BUY/SELL require symbol, quantity, price
    - CASH_DEPOSIT/CASH_WITHDRAW require cash_amount
    - Fractional shares supported via Decimal
    - USD only
    """

    txn_id: str
    account_id: str
    txn_time_est: datetime
    txn_type: TransactionType
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    cash_amount: Optional[Decimal] = None
    fees: Decimal = field(default_factory=lambda: Decimal("0"))
    note: Optional[str] = None
    is_deleted: bool = False
    created_at_est: Optional[datetime] = field(default=None)
    updated_at_est: Optional[datetime] = field(default=None)

    def __post_init__(self) -> None:
        if isinstance(self.txn_type, str):
            self.txn_type = TransactionType(self.txn_type)

    @property
    def is_stock_transaction(self) -> bool:
        """Return True if this is a BUY or SELL transaction."""
        return self.txn_type in (TransactionType.BUY, TransactionType.SELL)

    @property
    def is_cash_transaction(self) -> bool:
        """Return True if this is a CASH_DEPOSIT or CASH_WITHDRAW transaction."""
        return self.txn_type in (TransactionType.CASH_DEPOSIT, TransactionType.CASH_WITHDRAW)

    @property
    def net_cash_impact(self) -> Decimal:
        """
        Calculate net cash impact of this transaction.

        Positive = cash added, Negative = cash removed.
        """
        if self.txn_type == TransactionType.CASH_DEPOSIT:
            return self.cash_amount or Decimal("0")
        elif self.txn_type == TransactionType.CASH_WITHDRAW:
            return -(self.cash_amount or Decimal("0"))
        elif self.txn_type == TransactionType.BUY:
            total = (self.quantity or Decimal("0")) * (self.price or Decimal("0"))
            return -(total + self.fees)
        elif self.txn_type == TransactionType.SELL:
            total = (self.quantity or Decimal("0")) * (self.price or Decimal("0"))
            return total - self.fees
        return Decimal("0")


@dataclass
class TransactionRevision:
    """
    Audit trail for transaction changes.

    Records CREATE, UPDATE, SOFT_DELETE, and RESTORE actions
    with before/after JSON snapshots for undo capability.
    """

    rev_id: str
    txn_id: str
    rev_time_est: datetime
    action: RevisionAction
    before_json: Optional[str] = None  # JSON snapshot before change
    after_json: Optional[str] = None  # JSON snapshot after change

    def __post_init__(self) -> None:
        if isinstance(self.action, str):
            self.action = RevisionAction(self.action)
