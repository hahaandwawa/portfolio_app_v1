"""Transaction repository protocol."""

from datetime import datetime
from typing import Protocol, Optional

from app.domain.models import Transaction, TransactionRevision, TransactionType


class TransactionRepository(Protocol):
    """Interface for transaction (ledger) data access."""

    def create(self, transaction: Transaction) -> Transaction:
        """Persist a new transaction."""
        ...

    def get_by_id(self, txn_id: str) -> Optional[Transaction]:
        """Retrieve transaction by ID."""
        ...

    def update(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction."""
        ...

    def list_by_account(
        self,
        account_id: str,
        include_deleted: bool = False,
    ) -> list[Transaction]:
        """List all transactions for an account, ordered by txn_time_est."""
        ...

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
        ...

    def create_revision(self, revision: TransactionRevision) -> TransactionRevision:
        """Create a new revision record."""
        ...

    def get_latest_revision(self, account_id: str) -> Optional[TransactionRevision]:
        """Get the most recent revision for any transaction in the account."""
        ...

    def list_revisions_by_txn(self, txn_id: str) -> list[TransactionRevision]:
        """List all revisions for a transaction."""
        ...
