"""
Unit tests for LedgerService.

Tests cover:
- Account creation with cost basis method
- Transaction creation (BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAW)
- Transaction revisions (CREATE, UPDATE, SOFT_DELETE)
- Validation errors
- Edit and soft delete operations
- Undo functionality
"""

import json
import pytest
from decimal import Decimal
from datetime import datetime

from app.services import LedgerService
from app.services.ledger_service import TransactionCreate, TransactionUpdate
from app.domain.models import (
    Account,
    Transaction,
    TransactionType,
    CostBasisMethod,
    RevisionAction,
)
from app.core.exceptions import ValidationError, NotFoundError


# =============================================================================
# ACCOUNT CREATION TESTS
# =============================================================================


class TestCreateAccount:
    """Tests for account creation functionality."""

    def test_create_account_with_fifo_cost_basis(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN no accounts exist
        WHEN I create an account named "Brokerage" with cost_basis_method="FIFO"
        THEN the account is persisted with correct fields
        """
        account = ledger_service.create_account(
            name="Brokerage",
            cost_basis_method="FIFO",
        )

        assert account.account_id is not None
        assert account.name == "Brokerage"
        assert account.cost_basis_method == CostBasisMethod.FIFO
        assert account.created_at_est is not None

    def test_create_account_with_average_cost_basis(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN no accounts exist
        WHEN I create an account with cost_basis_method="AVERAGE"
        THEN the account is persisted with AVERAGE cost basis
        """
        account = ledger_service.create_account(
            name="IRA Account",
            cost_basis_method="AVERAGE",
        )

        assert account.cost_basis_method == CostBasisMethod.AVERAGE

    def test_create_account_default_cost_basis(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN no accounts exist
        WHEN I create an account without specifying cost basis method
        THEN the account uses FIFO as default
        """
        account = ledger_service.create_account(name="Default Account")

        assert account.cost_basis_method == CostBasisMethod.FIFO

    def test_create_duplicate_account_name_fails(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN an account named "Brokerage" already exists
        WHEN I attempt to create another account with the same name
        THEN a ValidationError is raised
        """
        ledger_service.create_account(name="Brokerage")

        with pytest.raises(ValidationError) as exc_info:
            ledger_service.create_account(name="Brokerage")

        assert "already exists" in str(exc_info.value.message)

    def test_list_accounts_returns_all(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN multiple accounts exist
        WHEN I list all accounts
        THEN all accounts are returned
        """
        ledger_service.create_account(name="Account 1")
        ledger_service.create_account(name="Account 2")
        ledger_service.create_account(name="Account 3")

        accounts = ledger_service.list_accounts()

        assert len(accounts) == 3
        names = {a.name for a in accounts}
        assert names == {"Account 1", "Account 2", "Account 3"}

    def test_get_account_by_id(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN an account exists
        WHEN I get the account by ID
        THEN the correct account is returned
        """
        created = ledger_service.create_account(name="Brokerage")

        retrieved = ledger_service.get_account(created.account_id)

        assert retrieved.account_id == created.account_id
        assert retrieved.name == "Brokerage"

    def test_get_nonexistent_account_raises(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN no account with specified ID exists
        WHEN I get the account by ID
        THEN NotFoundError is raised
        """
        with pytest.raises(NotFoundError):
            ledger_service.get_account("nonexistent-id")


# =============================================================================
# ADD TRANSACTION TESTS
# =============================================================================


class TestAddTransaction:
    """Tests for adding transactions to the ledger."""

    def test_add_buy_transaction(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a BUY transaction for 10 shares of AAPL at $185.00
        THEN the transaction is persisted with correct fields
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
            fees=Decimal("4.95"),
            note="Initial purchase",
        )

        txn = ledger_service.add_transaction(data)

        assert txn.txn_id is not None
        assert txn.account_id == sample_account.account_id
        assert txn.txn_type == TransactionType.BUY
        assert txn.symbol == "AAPL"
        assert txn.quantity == Decimal("10")
        assert txn.price == Decimal("185.00")
        assert txn.fees == Decimal("4.95")
        assert txn.note == "Initial purchase"
        assert txn.is_deleted is False
        assert txn.created_at_est is not None

    def test_add_buy_transaction_creates_revision(
        self,
        ledger_service: LedgerService,
        transaction_repo,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a BUY transaction
        THEN a TransactionRevision with action=CREATE is created
        AND before_json is None, after_json contains the transaction
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )

        txn = ledger_service.add_transaction(data)

        revisions = transaction_repo.list_revisions_by_txn(txn.txn_id)
        assert len(revisions) == 1

        rev = revisions[0]
        assert rev.action == RevisionAction.CREATE
        assert rev.before_json is None
        assert rev.after_json is not None

        after_data = json.loads(rev.after_json)
        assert after_data["symbol"] == "AAPL"
        assert after_data["quantity"] == "10"

    def test_add_cash_deposit_transaction(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a CASH_DEPOSIT of $10,000
        THEN the transaction is persisted correctly
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("10000.00"),
            note="Initial deposit",
        )

        txn = ledger_service.add_transaction(data)

        assert txn.txn_type == TransactionType.CASH_DEPOSIT
        assert txn.cash_amount == Decimal("10000.00")
        assert txn.symbol is None
        assert txn.quantity is None

    def test_add_cash_withdraw_transaction(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a CASH_WITHDRAW of $500
        THEN the transaction is persisted correctly
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.CASH_WITHDRAW,
            cash_amount=Decimal("500.00"),
        )

        txn = ledger_service.add_transaction(data)

        assert txn.txn_type == TransactionType.CASH_WITHDRAW
        assert txn.cash_amount == Decimal("500.00")

    def test_add_sell_transaction(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a SELL transaction
        THEN the transaction is persisted correctly
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.SELL,
            symbol="AAPL",
            quantity=Decimal("5"),
            price=Decimal("190.00"),
            fees=Decimal("4.95"),
        )

        txn = ledger_service.add_transaction(data)

        assert txn.txn_type == TransactionType.SELL
        assert txn.symbol == "AAPL"
        assert txn.quantity == Decimal("5")
        assert txn.price == Decimal("190.00")

    def test_symbol_is_uppercased(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a BUY with lowercase symbol
        THEN the symbol is stored uppercase
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="aapl",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )

        txn = ledger_service.add_transaction(data)

        assert txn.symbol == "AAPL"


# =============================================================================
# VALIDATION TESTS
# =============================================================================


class TestTransactionValidation:
    """Tests for transaction validation rules."""

    def test_buy_requires_symbol(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a BUY transaction without a symbol
        THEN ValidationError is raised
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol=None,  # Missing symbol
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )

        with pytest.raises(ValidationError) as exc_info:
            ledger_service.add_transaction(data)

        assert "BUY requires a symbol" in str(exc_info.value.message)

    def test_buy_requires_positive_quantity(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a BUY with quantity <= 0
        THEN ValidationError is raised
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("0"),  # Invalid: must be > 0
            price=Decimal("185.00"),
        )

        with pytest.raises(ValidationError) as exc_info:
            ledger_service.add_transaction(data)

        assert "requires quantity > 0" in str(exc_info.value.message)

    def test_buy_requires_non_negative_price(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a BUY with negative price
        THEN ValidationError is raised
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("-185.00"),  # Invalid: must be >= 0
        )

        with pytest.raises(ValidationError) as exc_info:
            ledger_service.add_transaction(data)

        assert "requires price >= 0" in str(exc_info.value.message)

    def test_buy_requires_non_negative_fees(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a BUY with negative fees
        THEN ValidationError is raised
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
            fees=Decimal("-4.95"),  # Invalid: must be >= 0
        )

        with pytest.raises(ValidationError) as exc_info:
            ledger_service.add_transaction(data)

        assert "Fees cannot be negative" in str(exc_info.value.message)

    def test_sell_requires_symbol(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a SELL without a symbol
        THEN ValidationError is raised
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.SELL,
            symbol=None,
            quantity=Decimal("5"),
            price=Decimal("190.00"),
        )

        with pytest.raises(ValidationError) as exc_info:
            ledger_service.add_transaction(data)

        assert "SELL requires a symbol" in str(exc_info.value.message)

    def test_cash_deposit_requires_positive_amount(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account exists
        WHEN I add a CASH_DEPOSIT with amount <= 0
        THEN ValidationError is raised
        """
        data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("0"),  # Invalid
        )

        with pytest.raises(ValidationError) as exc_info:
            ledger_service.add_transaction(data)

        assert "requires cash_amount > 0" in str(exc_info.value.message)

    def test_add_transaction_to_nonexistent_account(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN no account with specified ID exists
        WHEN I add a transaction
        THEN NotFoundError is raised
        """
        data = TransactionCreate(
            account_id="nonexistent-account",
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("10000.00"),
        )

        with pytest.raises(NotFoundError):
            ledger_service.add_transaction(data)


# =============================================================================
# EDIT TRANSACTION TESTS
# =============================================================================


class TestEditTransaction:
    """Tests for editing existing transactions."""

    def test_edit_transaction_updates_fields(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN a transaction exists
        WHEN I edit the transaction to change price
        THEN the transaction is updated
        """
        # Create initial transaction
        create_data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        txn = ledger_service.add_transaction(create_data)
        original_price = txn.price

        # Edit the transaction
        patch = TransactionUpdate(price=Decimal("186.00"))
        updated = ledger_service.edit_transaction(txn.txn_id, patch)

        assert updated.price == Decimal("186.00")
        assert updated.price != original_price
        assert updated.quantity == Decimal("10")  # Unchanged
        assert updated.updated_at_est is not None

    def test_edit_transaction_creates_update_revision(
        self,
        ledger_service: LedgerService,
        transaction_repo,
        sample_account: Account,
    ):
        """
        GIVEN a transaction exists
        WHEN I edit the transaction
        THEN an UPDATE revision is created with before/after snapshots
        """
        # Create initial transaction
        create_data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        txn = ledger_service.add_transaction(create_data)

        # Edit
        patch = TransactionUpdate(price=Decimal("186.00"))
        ledger_service.edit_transaction(txn.txn_id, patch)

        # Check revisions
        revisions = transaction_repo.list_revisions_by_txn(txn.txn_id)
        assert len(revisions) == 2  # CREATE + UPDATE

        update_rev = next(r for r in revisions if r.action == RevisionAction.UPDATE)
        assert update_rev.before_json is not None
        assert update_rev.after_json is not None

        before_data = json.loads(update_rev.before_json)
        after_data = json.loads(update_rev.after_json)

        assert before_data["price"] == "185.00"
        assert after_data["price"] == "186.00"

    def test_edit_multiple_fields(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN a transaction exists
        WHEN I edit multiple fields at once
        THEN all specified fields are updated
        """
        create_data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
            note="Original note",
        )
        txn = ledger_service.add_transaction(create_data)

        patch = TransactionUpdate(
            quantity=Decimal("15"),
            price=Decimal("186.00"),
            fees=Decimal("9.95"),
            note="Updated note",
        )
        updated = ledger_service.edit_transaction(txn.txn_id, patch)

        assert updated.quantity == Decimal("15")
        assert updated.price == Decimal("186.00")
        assert updated.fees == Decimal("9.95")
        assert updated.note == "Updated note"

    def test_edit_nonexistent_transaction_raises(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN no transaction with specified ID exists
        WHEN I edit the transaction
        THEN NotFoundError is raised
        """
        patch = TransactionUpdate(price=Decimal("186.00"))

        with pytest.raises(NotFoundError):
            ledger_service.edit_transaction("nonexistent-txn", patch)


# =============================================================================
# SOFT DELETE TESTS
# =============================================================================


class TestSoftDeleteTransaction:
    """Tests for soft deleting transactions."""

    def test_soft_delete_sets_is_deleted(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an active transaction exists
        WHEN I soft delete the transaction
        THEN is_deleted is set to True
        """
        create_data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        txn = ledger_service.add_transaction(create_data)

        ledger_service.soft_delete_transaction(txn.txn_id)

        # Query with include_deleted to get the deleted transaction
        transactions = ledger_service.query_transactions(
            account_ids=[sample_account.account_id],
            include_deleted=True,
        )
        deleted_txn = next(t for t in transactions if t.txn_id == txn.txn_id)

        assert deleted_txn.is_deleted is True

    def test_soft_delete_creates_revision(
        self,
        ledger_service: LedgerService,
        transaction_repo,
        sample_account: Account,
    ):
        """
        GIVEN an active transaction exists
        WHEN I soft delete the transaction
        THEN a SOFT_DELETE revision is created
        """
        create_data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        txn = ledger_service.add_transaction(create_data)

        ledger_service.soft_delete_transaction(txn.txn_id)

        revisions = transaction_repo.list_revisions_by_txn(txn.txn_id)
        assert len(revisions) == 2  # CREATE + SOFT_DELETE

        delete_rev = next(r for r in revisions if r.action == RevisionAction.SOFT_DELETE)
        assert delete_rev.before_json is not None
        assert delete_rev.after_json is not None

        before_data = json.loads(delete_rev.before_json)
        after_data = json.loads(delete_rev.after_json)

        assert before_data["is_deleted"] is False
        assert after_data["is_deleted"] is True

    def test_soft_delete_already_deleted_is_idempotent(
        self,
        ledger_service: LedgerService,
        transaction_repo,
        sample_account: Account,
    ):
        """
        GIVEN a transaction is already soft deleted
        WHEN I soft delete it again
        THEN no error is raised and no new revision is created
        """
        create_data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        txn = ledger_service.add_transaction(create_data)

        # Delete twice
        ledger_service.soft_delete_transaction(txn.txn_id)
        ledger_service.soft_delete_transaction(txn.txn_id)

        revisions = transaction_repo.list_revisions_by_txn(txn.txn_id)
        # Should only have CREATE + 1 SOFT_DELETE (not 2)
        delete_revisions = [r for r in revisions if r.action == RevisionAction.SOFT_DELETE]
        assert len(delete_revisions) == 1

    def test_soft_delete_nonexistent_transaction_raises(
        self,
        ledger_service: LedgerService,
    ):
        """
        GIVEN no transaction with specified ID exists
        WHEN I soft delete it
        THEN NotFoundError is raised
        """
        with pytest.raises(NotFoundError):
            ledger_service.soft_delete_transaction("nonexistent-txn")

    def test_cannot_edit_deleted_transaction(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN a transaction that has been soft deleted
        WHEN I attempt to edit it
        THEN ValidationError is raised
        """
        create_data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        txn = ledger_service.add_transaction(create_data)
        ledger_service.soft_delete_transaction(txn.txn_id)

        patch = TransactionUpdate(price=Decimal("186.00"))

        with pytest.raises(ValidationError) as exc_info:
            ledger_service.edit_transaction(txn.txn_id, patch)

        assert "Cannot edit a deleted transaction" in str(exc_info.value.message)


# =============================================================================
# QUERY TESTS
# =============================================================================


class TestQueryTransactions:
    """Tests for querying transactions."""

    def test_query_excludes_deleted_by_default(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN transactions exist, some deleted
        WHEN I query without include_deleted
        THEN only active transactions are returned
        """
        # Add 3 transactions
        for i in range(3):
            data = TransactionCreate(
                account_id=sample_account.account_id,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("185.00"),
            )
            txn = ledger_service.add_transaction(data)
            if i == 1:  # Delete middle transaction
                ledger_service.soft_delete_transaction(txn.txn_id)

        transactions = ledger_service.query_transactions(
            account_ids=[sample_account.account_id],
        )

        assert len(transactions) == 2
        assert all(not t.is_deleted for t in transactions)

    def test_query_includes_deleted_when_specified(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN transactions exist, some deleted
        WHEN I query with include_deleted=True
        THEN all transactions are returned
        """
        for i in range(3):
            data = TransactionCreate(
                account_id=sample_account.account_id,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("185.00"),
            )
            txn = ledger_service.add_transaction(data)
            if i == 1:
                ledger_service.soft_delete_transaction(txn.txn_id)

        transactions = ledger_service.query_transactions(
            account_ids=[sample_account.account_id],
            include_deleted=True,
        )

        assert len(transactions) == 3

    def test_query_by_symbol(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN transactions for multiple symbols exist
        WHEN I query by symbol
        THEN only matching transactions are returned
        """
        for symbol in ["AAPL", "AAPL", "MSFT", "GOOGL"]:
            data = TransactionCreate(
                account_id=sample_account.account_id,
                txn_type=TransactionType.BUY,
                symbol=symbol,
                quantity=Decimal("10"),
                price=Decimal("100.00"),
            )
            ledger_service.add_transaction(data)

        transactions = ledger_service.query_transactions(
            symbols=["AAPL"],
        )

        assert len(transactions) == 2
        assert all(t.symbol == "AAPL" for t in transactions)

    def test_query_by_transaction_type(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN transactions of various types exist
        WHEN I query by type
        THEN only matching transactions are returned
        """
        # Add various transaction types
        ledger_service.add_transaction(TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("10000"),
        ))
        ledger_service.add_transaction(TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        ledger_service.add_transaction(TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.SELL,
            symbol="AAPL",
            quantity=Decimal("5"),
            price=Decimal("190.00"),
        ))

        transactions = ledger_service.query_transactions(
            txn_types=[TransactionType.BUY, TransactionType.SELL],
        )

        assert len(transactions) == 2
        assert all(t.txn_type in [TransactionType.BUY, TransactionType.SELL] for t in transactions)


# =============================================================================
# UNDO TESTS
# =============================================================================


class TestUndoLastAction:
    """Tests for undo functionality."""

    def test_undo_with_no_actions_raises(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN an account with no transactions/revisions
        WHEN I call undo_last_action
        THEN ValidationError is raised
        """
        with pytest.raises((ValidationError, NotImplementedError)):
            ledger_service.undo_last_action(sample_account.account_id)

    # Note: Full undo implementation tests are pending as the functionality
    # is marked as TODO in the service. These test cases document expected behavior.

    @pytest.mark.skip(reason="Undo not yet implemented - documents expected behavior")
    def test_undo_soft_delete_restores_transaction(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN a transaction was soft deleted
        WHEN I call undo_last_action
        THEN the transaction is restored (is_deleted=False)
        """
        create_data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        txn = ledger_service.add_transaction(create_data)
        ledger_service.soft_delete_transaction(txn.txn_id)

        ledger_service.undo_last_action(sample_account.account_id)

        transactions = ledger_service.query_transactions(
            account_ids=[sample_account.account_id],
        )
        restored = next(t for t in transactions if t.txn_id == txn.txn_id)
        assert restored.is_deleted is False

    @pytest.mark.skip(reason="Undo not yet implemented - documents expected behavior")
    def test_undo_update_restores_previous_values(
        self,
        ledger_service: LedgerService,
        sample_account: Account,
    ):
        """
        GIVEN a transaction was edited
        WHEN I call undo_last_action
        THEN the previous values are restored
        """
        create_data = TransactionCreate(
            account_id=sample_account.account_id,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        txn = ledger_service.add_transaction(create_data)
        patch = TransactionUpdate(price=Decimal("186.00"))
        ledger_service.edit_transaction(txn.txn_id, patch)

        ledger_service.undo_last_action(sample_account.account_id)

        transactions = ledger_service.query_transactions(
            account_ids=[sample_account.account_id],
        )
        restored = next(t for t in transactions if t.txn_id == txn.txn_id)
        assert restored.price == Decimal("185.00")


# =============================================================================
# TRANSACTION NET CASH IMPACT TESTS
# =============================================================================


class TestTransactionNetCashImpact:
    """Tests for transaction cash impact calculation."""

    def test_cash_deposit_positive_impact(self):
        """
        GIVEN a CASH_DEPOSIT transaction of $10,000
        WHEN I calculate net_cash_impact
        THEN result is +$10,000
        """
        txn = Transaction(
            txn_id="test-1",
            account_id="acc-1",
            txn_time_est=datetime.now(),
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("10000.00"),
        )

        assert txn.net_cash_impact == Decimal("10000.00")

    def test_cash_withdraw_negative_impact(self):
        """
        GIVEN a CASH_WITHDRAW transaction of $500
        WHEN I calculate net_cash_impact
        THEN result is -$500
        """
        txn = Transaction(
            txn_id="test-1",
            account_id="acc-1",
            txn_time_est=datetime.now(),
            txn_type=TransactionType.CASH_WITHDRAW,
            cash_amount=Decimal("500.00"),
        )

        assert txn.net_cash_impact == Decimal("-500.00")

    def test_buy_negative_impact_includes_fees(self):
        """
        GIVEN a BUY transaction: 10 shares @ $185 with $5 fees
        WHEN I calculate net_cash_impact
        THEN result is -(10 * 185 + 5) = -$1,855
        """
        txn = Transaction(
            txn_id="test-1",
            account_id="acc-1",
            txn_time_est=datetime.now(),
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
            fees=Decimal("5.00"),
        )

        expected = Decimal("-1855.00")
        assert txn.net_cash_impact == expected

    def test_sell_positive_impact_minus_fees(self):
        """
        GIVEN a SELL transaction: 5 shares @ $190 with $5 fees
        WHEN I calculate net_cash_impact
        THEN result is (5 * 190) - 5 = $945
        """
        txn = Transaction(
            txn_id="test-1",
            account_id="acc-1",
            txn_time_est=datetime.now(),
            txn_type=TransactionType.SELL,
            symbol="AAPL",
            quantity=Decimal("5"),
            price=Decimal("190.00"),
            fees=Decimal("5.00"),
        )

        expected = Decimal("945.00")
        assert txn.net_cash_impact == expected
