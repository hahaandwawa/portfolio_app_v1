"""
Integration tests for SQLAlchemy repositories with SQLite.

Tests cover:
- Account repository CRUD operations
- Transaction repository CRUD and query operations
- Cache repository operations
- Data persistence across queries
"""

import pytest
from decimal import Decimal
from datetime import datetime

from sqlalchemy.orm import Session

from app.repositories.sqlalchemy import (
    SqlAlchemyAccountRepository,
    SqlAlchemyTransactionRepository,
    SqlAlchemyCacheRepository,
)
from app.domain.models import (
    Account,
    Transaction,
    TransactionRevision,
    TransactionType,
    CostBasisMethod,
    RevisionAction,
    PositionCache,
    CashCache,
)

from tests.conftest import eastern_datetime


# =============================================================================
# ACCOUNT REPOSITORY TESTS
# =============================================================================


class TestAccountRepository:
    """Tests for SqlAlchemyAccountRepository."""

    def test_create_account_persists(
        self,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN an in-memory SQLite database
        WHEN I create an account
        THEN the account can be retrieved by ID
        """
        account = Account(
            account_id="acc-001",
            name="Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        )

        created = account_repo.create(account)
        retrieved = account_repo.get_by_id("acc-001")

        assert retrieved is not None
        assert retrieved.account_id == "acc-001"
        assert retrieved.name == "Brokerage"
        assert retrieved.cost_basis_method == CostBasisMethod.FIFO

    def test_get_by_name(
        self,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN an account exists
        WHEN I retrieve by name
        THEN correct account is returned
        """
        account = Account(
            account_id="acc-001",
            name="My Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        )
        account_repo.create(account)

        retrieved = account_repo.get_by_name("My Brokerage")

        assert retrieved is not None
        assert retrieved.account_id == "acc-001"

    def test_get_by_name_not_found(
        self,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN no account with given name
        WHEN I retrieve by name
        THEN None is returned
        """
        retrieved = account_repo.get_by_name("Nonexistent")

        assert retrieved is None

    def test_list_all_accounts(
        self,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN multiple accounts exist
        WHEN I list all
        THEN all accounts are returned
        """
        for i in range(3):
            account_repo.create(Account(
                account_id=f"acc-00{i}",
                name=f"Account {i}",
                cost_basis_method=CostBasisMethod.FIFO,
                created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
            ))

        accounts = account_repo.list_all()

        assert len(accounts) == 3

    def test_update_account(
        self,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN an account exists
        WHEN I update it
        THEN changes are persisted
        """
        account = Account(
            account_id="acc-001",
            name="Old Name",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        )
        account_repo.create(account)

        account.name = "New Name"
        account_repo.update(account)

        retrieved = account_repo.get_by_id("acc-001")
        assert retrieved.name == "New Name"

    def test_delete_account(
        self,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN an account exists
        WHEN I delete it
        THEN it cannot be retrieved
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="To Delete",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        account_repo.delete("acc-001")

        retrieved = account_repo.get_by_id("acc-001")
        assert retrieved is None


# =============================================================================
# TRANSACTION REPOSITORY TESTS
# =============================================================================


class TestTransactionRepository:
    """Tests for SqlAlchemyTransactionRepository."""

    def test_create_transaction_persists(
        self,
        transaction_repo: SqlAlchemyTransactionRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN an account exists
        WHEN I create a transaction
        THEN it can be retrieved by ID
        """
        # Create account first (foreign key)
        account_repo.create(Account(
            account_id="acc-001",
            name="Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        transaction = Transaction(
            txn_id="txn-001",
            account_id="acc-001",
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
            fees=Decimal("4.95"),
        )

        transaction_repo.create(transaction)
        retrieved = transaction_repo.get_by_id("txn-001")

        assert retrieved is not None
        assert retrieved.txn_id == "txn-001"
        assert retrieved.symbol == "AAPL"
        assert retrieved.quantity == Decimal("10")

    def test_update_transaction(
        self,
        transaction_repo: SqlAlchemyTransactionRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN a transaction exists
        WHEN I update it
        THEN changes are persisted
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        transaction = Transaction(
            txn_id="txn-001",
            account_id="acc-001",
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        transaction_repo.create(transaction)

        transaction.price = Decimal("186.00")
        transaction.is_deleted = True
        transaction_repo.update(transaction)

        retrieved = transaction_repo.get_by_id("txn-001")
        assert retrieved.price == Decimal("186.00")
        assert retrieved.is_deleted is True

    def test_list_by_account(
        self,
        transaction_repo: SqlAlchemyTransactionRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN multiple transactions for an account
        WHEN I list by account
        THEN only that account's transactions are returned
        """
        # Create accounts
        account_repo.create(Account(
            account_id="acc-001",
            name="Account 1",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))
        account_repo.create(Account(
            account_id="acc-002",
            name="Account 2",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        # Create transactions
        for i in range(3):
            transaction_repo.create(Transaction(
                txn_id=f"txn-1-{i}",
                account_id="acc-001",
                txn_time_est=eastern_datetime(2024, 1, 15 + i, 14, 0),
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("1000"),
            ))
        transaction_repo.create(Transaction(
            txn_id="txn-2-0",
            account_id="acc-002",
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("1000"),
        ))

        transactions = transaction_repo.list_by_account("acc-001")

        assert len(transactions) == 3
        assert all(t.account_id == "acc-001" for t in transactions)

    def test_list_by_account_excludes_deleted(
        self,
        transaction_repo: SqlAlchemyTransactionRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN some transactions are deleted
        WHEN I list by account with include_deleted=False
        THEN deleted transactions are excluded
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Account 1",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        # Active transaction
        transaction_repo.create(Transaction(
            txn_id="txn-001",
            account_id="acc-001",
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("1000"),
            is_deleted=False,
        ))
        # Deleted transaction
        transaction_repo.create(Transaction(
            txn_id="txn-002",
            account_id="acc-001",
            txn_time_est=eastern_datetime(2024, 1, 16, 14, 0),
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("2000"),
            is_deleted=True,
        ))

        transactions = transaction_repo.list_by_account("acc-001", include_deleted=False)

        assert len(transactions) == 1
        assert transactions[0].txn_id == "txn-001"

    def test_list_by_account_includes_deleted_when_specified(
        self,
        transaction_repo: SqlAlchemyTransactionRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN some transactions are deleted
        WHEN I list by account with include_deleted=True
        THEN all transactions are returned
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Account 1",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        transaction_repo.create(Transaction(
            txn_id="txn-001",
            account_id="acc-001",
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("1000"),
            is_deleted=False,
        ))
        transaction_repo.create(Transaction(
            txn_id="txn-002",
            account_id="acc-001",
            txn_time_est=eastern_datetime(2024, 1, 16, 14, 0),
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("2000"),
            is_deleted=True,
        ))

        transactions = transaction_repo.list_by_account("acc-001", include_deleted=True)

        assert len(transactions) == 2

    def test_create_revision(
        self,
        transaction_repo: SqlAlchemyTransactionRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN a transaction exists
        WHEN I create a revision
        THEN the revision is persisted
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Account 1",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))
        transaction_repo.create(Transaction(
            txn_id="txn-001",
            account_id="acc-001",
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))

        revision = TransactionRevision(
            rev_id="rev-001",
            txn_id="txn-001",
            rev_time_est=eastern_datetime(2024, 1, 15, 14, 0),
            action=RevisionAction.CREATE,
            before_json=None,
            after_json='{"symbol": "AAPL"}',
        )

        created_rev = transaction_repo.create_revision(revision)
        revisions = transaction_repo.list_revisions_by_txn("txn-001")

        assert len(revisions) == 1
        assert revisions[0].action == RevisionAction.CREATE

    def test_list_revisions_by_txn(
        self,
        transaction_repo: SqlAlchemyTransactionRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN multiple revisions for a transaction
        WHEN I list revisions
        THEN all are returned
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Account 1",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))
        transaction_repo.create(Transaction(
            txn_id="txn-001",
            account_id="acc-001",
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))

        # Create revisions
        for i, action in enumerate([RevisionAction.CREATE, RevisionAction.UPDATE]):
            transaction_repo.create_revision(TransactionRevision(
                rev_id=f"rev-00{i}",
                txn_id="txn-001",
                rev_time_est=eastern_datetime(2024, 1, 15 + i, 14, 0),
                action=action,
            ))

        revisions = transaction_repo.list_revisions_by_txn("txn-001")

        assert len(revisions) == 2


# =============================================================================
# CACHE REPOSITORY TESTS
# =============================================================================


class TestCacheRepository:
    """Tests for SqlAlchemyCacheRepository."""

    def test_upsert_position_insert(
        self,
        cache_repo: SqlAlchemyCacheRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN no existing position
        WHEN I upsert a position
        THEN it is inserted
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        position = PositionCache(
            account_id="acc-001",
            symbol="AAPL",
            shares=Decimal("10"),
            last_rebuilt_at_est=eastern_datetime(2024, 6, 15, 14, 0),
        )

        cache_repo.upsert_position(position)
        retrieved = cache_repo.get_position("acc-001", "AAPL")

        assert retrieved is not None
        assert retrieved.shares == Decimal("10")

    def test_upsert_position_update(
        self,
        cache_repo: SqlAlchemyCacheRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN existing position
        WHEN I upsert with new values
        THEN it is updated
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        # Initial insert
        cache_repo.upsert_position(PositionCache(
            account_id="acc-001",
            symbol="AAPL",
            shares=Decimal("10"),
        ))

        # Update
        cache_repo.upsert_position(PositionCache(
            account_id="acc-001",
            symbol="AAPL",
            shares=Decimal("15"),
        ))

        retrieved = cache_repo.get_position("acc-001", "AAPL")
        assert retrieved.shares == Decimal("15")

    def test_get_positions(
        self,
        cache_repo: SqlAlchemyCacheRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN multiple positions for an account
        WHEN I get positions
        THEN all are returned
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        for symbol in ["AAPL", "MSFT", "GOOGL"]:
            cache_repo.upsert_position(PositionCache(
                account_id="acc-001",
                symbol=symbol,
                shares=Decimal("10"),
            ))

        positions = cache_repo.get_positions("acc-001")

        assert len(positions) == 3

    def test_delete_positions(
        self,
        cache_repo: SqlAlchemyCacheRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN positions exist
        WHEN I delete positions for an account
        THEN all are removed
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        for symbol in ["AAPL", "MSFT"]:
            cache_repo.upsert_position(PositionCache(
                account_id="acc-001",
                symbol=symbol,
                shares=Decimal("10"),
            ))

        cache_repo.delete_positions("acc-001")
        positions = cache_repo.get_positions("acc-001")

        assert len(positions) == 0

    def test_upsert_cash(
        self,
        cache_repo: SqlAlchemyCacheRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN no existing cash cache
        WHEN I upsert cash
        THEN it is persisted
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        cash = CashCache(
            account_id="acc-001",
            cash_balance=Decimal("10000.00"),
        )

        cache_repo.upsert_cash(cash)
        retrieved = cache_repo.get_cash("acc-001")

        assert retrieved is not None
        assert retrieved.cash_balance == Decimal("10000.00")

    def test_delete_cash(
        self,
        cache_repo: SqlAlchemyCacheRepository,
        account_repo: SqlAlchemyAccountRepository,
    ):
        """
        GIVEN cash cache exists
        WHEN I delete cash
        THEN it is removed
        """
        account_repo.create(Account(
            account_id="acc-001",
            name="Brokerage",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        cache_repo.upsert_cash(CashCache(
            account_id="acc-001",
            cash_balance=Decimal("10000.00"),
        ))

        cache_repo.delete_cash("acc-001")
        retrieved = cache_repo.get_cash("acc-001")

        assert retrieved is None


# =============================================================================
# SESSION PERSISTENCE TESTS
# =============================================================================


class TestSessionPersistence:
    """Tests for data persistence within a session."""

    def test_data_persists_across_queries(
        self,
        account_repo: SqlAlchemyAccountRepository,
        transaction_repo: SqlAlchemyTransactionRepository,
    ):
        """
        GIVEN I create data in one query
        WHEN I query again in the same session
        THEN data is available
        """
        # Create account
        account_repo.create(Account(
            account_id="acc-001",
            name="Test Account",
            cost_basis_method=CostBasisMethod.FIFO,
            created_at_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))

        # Create transaction
        transaction_repo.create(Transaction(
            txn_id="txn-001",
            account_id="acc-001",
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))

        # Query again
        accounts = account_repo.list_all()
        transactions = transaction_repo.list_by_account("acc-001")

        assert len(accounts) == 1
        assert len(transactions) == 1
        assert transactions[0].symbol == "AAPL"
