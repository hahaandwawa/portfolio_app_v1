"""Enumerations for domain models."""

from enum import Enum


class TransactionType(str, Enum):
    """Types of ledger transactions."""

    BUY = "BUY"
    SELL = "SELL"
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAW = "CASH_WITHDRAW"


class CostBasisMethod(str, Enum):
    """Cost basis calculation methods."""

    FIFO = "FIFO"  # First In, First Out (default, implemented)
    AVERAGE = "AVERAGE"  # Average cost (stub support)
    # LIFO and SPECIFIC_ID deferred


class RevisionAction(str, Enum):
    """Actions recorded in transaction revisions."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    SOFT_DELETE = "SOFT_DELETE"
    RESTORE = "RESTORE"
