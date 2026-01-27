"""SQLAlchemy ORM model definitions."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Text,
    ForeignKey,
    Numeric,
    Enum as SqlEnum,
)
from sqlalchemy.orm import relationship

from app.repositories.sqlalchemy.database import Base
from app.domain.models.enums import TransactionType, CostBasisMethod, RevisionAction


class AccountORM(Base):
    """SQLAlchemy model for Account."""

    __tablename__ = "accounts"

    account_id = Column(String(36), primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    cost_basis_method = Column(
        SqlEnum(CostBasisMethod),
        default=CostBasisMethod.FIFO,
        nullable=False,
    )
    created_at_est = Column(DateTime, nullable=False, default=datetime.utcnow)

    transactions = relationship("TransactionORM", back_populates="account")


class TransactionORM(Base):
    """SQLAlchemy model for Transaction (ledger entry)."""

    __tablename__ = "transactions"

    txn_id = Column(String(36), primary_key=True)
    account_id = Column(String(36), ForeignKey("accounts.account_id"), nullable=False)
    txn_time_est = Column(DateTime, nullable=False)
    txn_type = Column(SqlEnum(TransactionType), nullable=False)
    symbol = Column(String(20), nullable=True)
    quantity = Column(Numeric(precision=18, scale=8), nullable=True)
    price = Column(Numeric(precision=18, scale=4), nullable=True)
    cash_amount = Column(Numeric(precision=18, scale=2), nullable=True)
    fees = Column(Numeric(precision=18, scale=2), default=Decimal("0"))
    note = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)
    created_at_est = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at_est = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    account = relationship("AccountORM", back_populates="transactions")
    revisions = relationship("TransactionRevisionORM", back_populates="transaction")


class TransactionRevisionORM(Base):
    """SQLAlchemy model for TransactionRevision (audit trail)."""

    __tablename__ = "transaction_revisions"

    rev_id = Column(String(36), primary_key=True)
    txn_id = Column(String(36), ForeignKey("transactions.txn_id"), nullable=False)
    rev_time_est = Column(DateTime, nullable=False)
    action = Column(SqlEnum(RevisionAction), nullable=False)
    before_json = Column(Text, nullable=True)
    after_json = Column(Text, nullable=True)

    transaction = relationship("TransactionORM", back_populates="revisions")


class PositionCacheORM(Base):
    """SQLAlchemy model for PositionCache (derived holdings)."""

    __tablename__ = "position_cache"

    account_id = Column(String(36), ForeignKey("accounts.account_id"), primary_key=True)
    symbol = Column(String(20), primary_key=True)
    shares = Column(Numeric(precision=18, scale=8), default=Decimal("0"))
    last_rebuilt_at_est = Column(DateTime, nullable=True)


class CashCacheORM(Base):
    """SQLAlchemy model for CashCache (derived cash balance)."""

    __tablename__ = "cash_cache"

    account_id = Column(String(36), ForeignKey("accounts.account_id"), primary_key=True)
    cash_balance = Column(Numeric(precision=18, scale=2), default=Decimal("0"))
    last_rebuilt_at_est = Column(DateTime, nullable=True)
