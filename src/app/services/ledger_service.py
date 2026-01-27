"""Ledger service for transaction management."""

import json
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Optional

from app.core.timezone import now_eastern
from app.core.exceptions import ValidationError, NotFoundError
from app.domain.models import (
    Account,
    Transaction,
    TransactionRevision,
    TransactionType,
    CostBasisMethod,
    RevisionAction,
)
from app.repositories.protocols import AccountRepository, TransactionRepository


@dataclass
class TransactionCreate:
    """Input data for creating a transaction."""

    account_id: str
    txn_type: TransactionType
    txn_time_est: Optional[datetime] = None
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    cash_amount: Optional[Decimal] = None
    fees: Decimal = Decimal("0")
    note: Optional[str] = None


@dataclass
class TransactionUpdate:
    """Partial update data for editing a transaction."""

    txn_time_est: Optional[datetime] = None
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    cash_amount: Optional[Decimal] = None
    fees: Optional[Decimal] = None
    note: Optional[str] = None


class LedgerService:
    """
    Service for managing the transaction ledger.

    Handles account creation, transaction CRUD, and audit trail.
    Ledger is the source of truth; all mutations are tracked via revisions.
    """

    def __init__(
        self,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
    ):
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo

    def create_account(
        self,
        name: str,
        cost_basis_method: str = "FIFO",
    ) -> Account:
        """
        Create a new investment account.

        Args:
            name: Unique account name
            cost_basis_method: FIFO (default) or AVERAGE

        Returns:
            Created Account instance
        """
        existing = self._account_repo.get_by_name(name)
        if existing:
            raise ValidationError(f"Account with name '{name}' already exists")

        account = Account(
            account_id=str(uuid.uuid4()),
            name=name,
            cost_basis_method=CostBasisMethod(cost_basis_method),
            created_at_est=now_eastern(),
        )
        return self._account_repo.create(account)

    def get_account(self, account_id: str) -> Account:
        """Get account by ID."""
        account = self._account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account", account_id)
        return account

    def list_accounts(self) -> list[Account]:
        """List all accounts."""
        return self._account_repo.list_all()

    def add_transaction(self, data: TransactionCreate) -> Transaction:
        """
        Add a new transaction to the ledger.

        Validates input based on transaction type and creates audit revision.
        """
        self._validate_transaction_create(data)

        txn_time = data.txn_time_est or now_eastern()
        transaction = Transaction(
            txn_id=str(uuid.uuid4()),
            account_id=data.account_id,
            txn_time_est=txn_time,
            txn_type=data.txn_type,
            symbol=data.symbol.upper() if data.symbol else None,
            quantity=data.quantity,
            price=data.price,
            cash_amount=data.cash_amount,
            fees=data.fees,
            note=data.note,
            is_deleted=False,
            created_at_est=now_eastern(),
        )

        created = self._transaction_repo.create(transaction)
        self._create_revision(created, RevisionAction.CREATE, before=None)
        return created

    def edit_transaction(
        self,
        transaction_id: str,
        patch: TransactionUpdate,
    ) -> Transaction:
        """
        Edit an existing transaction.

        Creates revision with before/after snapshots.
        """
        transaction = self._transaction_repo.get_by_id(transaction_id)
        if not transaction:
            raise NotFoundError("Transaction", transaction_id)
        if transaction.is_deleted:
            raise ValidationError("Cannot edit a deleted transaction")

        before_snapshot = self._to_json(transaction)

        # Apply patch
        if patch.txn_time_est is not None:
            transaction.txn_time_est = patch.txn_time_est
        if patch.symbol is not None:
            transaction.symbol = patch.symbol.upper()
        if patch.quantity is not None:
            transaction.quantity = patch.quantity
        if patch.price is not None:
            transaction.price = patch.price
        if patch.cash_amount is not None:
            transaction.cash_amount = patch.cash_amount
        if patch.fees is not None:
            transaction.fees = patch.fees
        if patch.note is not None:
            transaction.note = patch.note

        transaction.updated_at_est = now_eastern()

        updated = self._transaction_repo.update(transaction)
        self._create_revision(updated, RevisionAction.UPDATE, before=before_snapshot)
        return updated

    def soft_delete_transaction(self, transaction_id: str) -> None:
        """
        Soft delete a transaction (mark as deleted, retain record).

        Creates revision for undo capability.
        """
        transaction = self._transaction_repo.get_by_id(transaction_id)
        if not transaction:
            raise NotFoundError("Transaction", transaction_id)
        if transaction.is_deleted:
            return  # Already deleted

        before_snapshot = self._to_json(transaction)
        transaction.is_deleted = True
        transaction.updated_at_est = now_eastern()

        self._transaction_repo.update(transaction)
        self._create_revision(transaction, RevisionAction.SOFT_DELETE, before=before_snapshot)

    def undo_last_action(self, account_id: str) -> None:
        """
        Undo the last action on the account (restore from revision).

        TODO: Implement full undo logic using before_json snapshot.
        """
        latest_revision = self._transaction_repo.get_latest_revision(account_id)
        if not latest_revision:
            raise ValidationError("No actions to undo for this account")

        # TODO: Implement restore logic based on revision action type
        # - CREATE: soft delete the transaction
        # - UPDATE: restore before_json state
        # - SOFT_DELETE: restore (undelete)
        # - RESTORE: re-delete
        raise NotImplementedError("Undo functionality not yet implemented")

    def query_transactions(
        self,
        account_ids: Optional[list[str]] = None,
        symbols: Optional[list[str]] = None,
        txn_types: Optional[list[TransactionType]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_deleted: bool = False,
    ) -> list[Transaction]:
        """Query transactions with filters."""
        return self._transaction_repo.query(
            account_ids=account_ids,
            symbols=symbols,
            txn_types=txn_types,
            start_date=start_date,
            end_date=end_date,
            include_deleted=include_deleted,
        )

    def _validate_transaction_create(self, data: TransactionCreate) -> None:
        """Validate transaction creation input."""
        # Check account exists
        account = self._account_repo.get_by_id(data.account_id)
        if not account:
            raise NotFoundError("Account", data.account_id)

        if data.txn_type in (TransactionType.BUY, TransactionType.SELL):
            if not data.symbol:
                raise ValidationError(f"{data.txn_type.value} requires a symbol")
            if data.quantity is None or data.quantity <= 0:
                raise ValidationError(f"{data.txn_type.value} requires quantity > 0")
            if data.price is None or data.price < 0:
                raise ValidationError(f"{data.txn_type.value} requires price >= 0")
            if data.fees < 0:
                raise ValidationError("Fees cannot be negative")

            # TODO: For SELL, validate sufficient shares via PortfolioEngine

        elif data.txn_type in (TransactionType.CASH_DEPOSIT, TransactionType.CASH_WITHDRAW):
            if data.cash_amount is None or data.cash_amount <= 0:
                raise ValidationError(f"{data.txn_type.value} requires cash_amount > 0")

            # TODO: For CASH_WITHDRAW, validate sufficient cash if enforce_cash_balance

    def _create_revision(
        self,
        transaction: Transaction,
        action: RevisionAction,
        before: Optional[str],
    ) -> TransactionRevision:
        """Create audit revision for a transaction change."""
        revision = TransactionRevision(
            rev_id=str(uuid.uuid4()),
            txn_id=transaction.txn_id,
            rev_time_est=now_eastern(),
            action=action,
            before_json=before,
            after_json=self._to_json(transaction),
        )
        return self._transaction_repo.create_revision(revision)

    @staticmethod
    def _to_json(transaction: Transaction) -> str:
        """Serialize transaction to JSON for revision storage."""
        data = asdict(transaction)
        # Convert non-serializable types
        for key, value in data.items():
            if isinstance(value, Decimal):
                data[key] = str(value)
            elif isinstance(value, datetime):
                data[key] = value.isoformat()
            elif hasattr(value, "value"):  # Enum
                data[key] = value.value
        return json.dumps(data)
