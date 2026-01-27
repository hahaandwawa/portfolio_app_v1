"""SQLAlchemy implementation of TransactionRepository."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.domain.models import Transaction, TransactionRevision, TransactionType
from app.repositories.sqlalchemy.orm_models import TransactionORM, TransactionRevisionORM


class SqlAlchemyTransactionRepository:
    """SQLAlchemy-backed transaction repository."""

    def __init__(self, db: Session):
        self._db = db

    def create(self, transaction: Transaction) -> Transaction:
        """Persist a new transaction."""
        orm_txn = self._to_orm(transaction)
        self._db.add(orm_txn)
        self._db.commit()
        self._db.refresh(orm_txn)
        return self._to_domain(orm_txn)

    def get_by_id(self, txn_id: str) -> Optional[Transaction]:
        """Retrieve transaction by ID."""
        orm_txn = self._db.query(TransactionORM).filter(
            TransactionORM.txn_id == txn_id
        ).first()
        return self._to_domain(orm_txn) if orm_txn else None

    def update(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction."""
        orm_txn = self._db.query(TransactionORM).filter(
            TransactionORM.txn_id == transaction.txn_id
        ).first()
        if not orm_txn:
            raise ValueError(f"Transaction not found: {transaction.txn_id}")

        orm_txn.txn_time_est = transaction.txn_time_est
        orm_txn.txn_type = transaction.txn_type
        orm_txn.symbol = transaction.symbol
        orm_txn.quantity = transaction.quantity
        orm_txn.price = transaction.price
        orm_txn.cash_amount = transaction.cash_amount
        orm_txn.fees = transaction.fees
        orm_txn.note = transaction.note
        orm_txn.is_deleted = transaction.is_deleted
        orm_txn.updated_at_est = datetime.utcnow()

        self._db.commit()
        self._db.refresh(orm_txn)
        return self._to_domain(orm_txn)

    def list_by_account(
        self,
        account_id: str,
        include_deleted: bool = False,
    ) -> list[Transaction]:
        """List all transactions for an account, ordered by txn_time_est."""
        query = self._db.query(TransactionORM).filter(
            TransactionORM.account_id == account_id
        )
        if not include_deleted:
            query = query.filter(TransactionORM.is_deleted == False)  # noqa: E712
        query = query.order_by(TransactionORM.txn_time_est)
        return [self._to_domain(t) for t in query.all()]

    def query(
        self,
        account_ids: Optional[list[str]] = None,
        symbols: Optional[list[str]] = None,
        txn_types: Optional[list[TransactionType]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_deleted: bool = False,
    ) -> list[Transaction]:
        """Query transactions with filters."""
        query = self._db.query(TransactionORM)

        conditions = []
        if account_ids:
            conditions.append(TransactionORM.account_id.in_(account_ids))
        if symbols:
            conditions.append(TransactionORM.symbol.in_(symbols))
        if txn_types:
            conditions.append(TransactionORM.txn_type.in_(txn_types))
        if start_date:
            conditions.append(TransactionORM.txn_time_est >= start_date)
        if end_date:
            conditions.append(TransactionORM.txn_time_est <= end_date)
        if not include_deleted:
            conditions.append(TransactionORM.is_deleted == False)  # noqa: E712

        if conditions:
            query = query.filter(and_(*conditions))

        query = query.order_by(TransactionORM.txn_time_est)
        return [self._to_domain(t) for t in query.all()]

    def create_revision(self, revision: TransactionRevision) -> TransactionRevision:
        """Create a new revision record."""
        orm_rev = TransactionRevisionORM(
            rev_id=revision.rev_id,
            txn_id=revision.txn_id,
            rev_time_est=revision.rev_time_est,
            action=revision.action,
            before_json=revision.before_json,
            after_json=revision.after_json,
        )
        self._db.add(orm_rev)
        self._db.commit()
        self._db.refresh(orm_rev)
        return self._revision_to_domain(orm_rev)

    def get_latest_revision(self, account_id: str) -> Optional[TransactionRevision]:
        """Get the most recent revision for any transaction in the account."""
        orm_rev = (
            self._db.query(TransactionRevisionORM)
            .join(TransactionORM)
            .filter(TransactionORM.account_id == account_id)
            .order_by(TransactionRevisionORM.rev_time_est.desc())
            .first()
        )
        return self._revision_to_domain(orm_rev) if orm_rev else None

    def list_revisions_by_txn(self, txn_id: str) -> list[TransactionRevision]:
        """List all revisions for a transaction."""
        orm_revs = (
            self._db.query(TransactionRevisionORM)
            .filter(TransactionRevisionORM.txn_id == txn_id)
            .order_by(TransactionRevisionORM.rev_time_est)
            .all()
        )
        return [self._revision_to_domain(r) for r in orm_revs]

    def _to_orm(self, txn: Transaction) -> TransactionORM:
        """Convert domain model to ORM model."""
        return TransactionORM(
            txn_id=txn.txn_id,
            account_id=txn.account_id,
            txn_time_est=txn.txn_time_est,
            txn_type=txn.txn_type,
            symbol=txn.symbol,
            quantity=txn.quantity,
            price=txn.price,
            cash_amount=txn.cash_amount,
            fees=txn.fees,
            note=txn.note,
            is_deleted=txn.is_deleted,
            created_at_est=txn.created_at_est,
            updated_at_est=txn.updated_at_est,
        )

    @staticmethod
    def _to_domain(orm: TransactionORM) -> Transaction:
        """Convert ORM model to domain model."""
        return Transaction(
            txn_id=orm.txn_id,
            account_id=orm.account_id,
            txn_time_est=orm.txn_time_est,
            txn_type=orm.txn_type,
            symbol=orm.symbol,
            quantity=Decimal(str(orm.quantity)) if orm.quantity else None,
            price=Decimal(str(orm.price)) if orm.price else None,
            cash_amount=Decimal(str(orm.cash_amount)) if orm.cash_amount else None,
            fees=Decimal(str(orm.fees)) if orm.fees else Decimal("0"),
            note=orm.note,
            is_deleted=orm.is_deleted,
            created_at_est=orm.created_at_est,
            updated_at_est=orm.updated_at_est,
        )

    @staticmethod
    def _revision_to_domain(orm: TransactionRevisionORM) -> TransactionRevision:
        """Convert ORM revision to domain model."""
        return TransactionRevision(
            rev_id=orm.rev_id,
            txn_id=orm.txn_id,
            rev_time_est=orm.rev_time_est,
            action=orm.action,
            before_json=orm.before_json,
            after_json=orm.after_json,
        )
