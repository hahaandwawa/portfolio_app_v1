from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.data.enum import TransactionType

@dataclass
class Transaction:
    """
    Transaction entry

    Supports: BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAW.
    - BUY/SELL require stock symbol, quantity, price
    - CASH_DEPOSIT/CASH_WITHDRAW require cash_amount
    - Fractional shares supported via Decimal
    - currently supporting USD as the only currency
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