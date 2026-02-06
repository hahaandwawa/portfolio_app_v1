"""
Tests for TransactionService.
Covers every public and validation path: common and edge cases.
"""
from datetime import datetime
from decimal import Decimal

import pytest

from src.service.transaction_service import (
    TransactionService,
    TransactionCreate,
    TransactionEdit,
)
from src.service.account_service import AccountCreate
from src.service.enums import TransactionType
from src.utils.exceptions import ValidationError, NotFoundError

from src.tests.conftest import make_transaction_create


# -----------------------------------------------------------------------------
# __init__
# -----------------------------------------------------------------------------

class TestTransactionServiceInit:
    """TransactionService initialization with explicit DB paths."""

    def test_init_with_both_paths(self, account_db_path, transaction_db_path):
        svc = TransactionService(
            transaction_db_path=transaction_db_path,
            account_db_path=account_db_path,
        )
        assert svc._transaction_db_path == transaction_db_path
        assert svc._account_db_path == account_db_path


# -----------------------------------------------------------------------------
# _validate_account (via create) — account must exist
# -----------------------------------------------------------------------------

class TestTransactionValidateAccount:
    """Transaction create fails when account does not exist."""

    def test_create_transaction_account_not_found_raises(
        self, transaction_service, transaction_db_path
    ):
        # No account in DB
        txn = make_transaction_create(account_name="NonExistentAccount")
        with pytest.raises(NotFoundError) as exc_info:
            transaction_service.create_transaction(txn)
        assert "Account" in exc_info.value.message or "not found" in exc_info.value.message.lower()
        assert "NonExistentAccount" in exc_info.value.message


# -----------------------------------------------------------------------------
# _validate_transaction_create: BUY / SELL
# -----------------------------------------------------------------------------

class TestValidateTransactionCreateBuySell:
    """Validation for BUY and SELL: symbol, quantity, price, fees, txn_time_est."""

    def test_buy_missing_symbol_raises(self, transaction_service, account_for_transactions):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            symbol=None,
        )
        with pytest.raises(ValidationError) as exc_info:
            transaction_service.create_transaction(txn)
        assert "symbol" in exc_info.value.message.lower()

    def test_buy_quantity_zero_raises(self, transaction_service, account_for_transactions):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            quantity=Decimal("0"),
        )
        with pytest.raises(ValidationError) as exc_info:
            transaction_service.create_transaction(txn)
        assert "quantity" in exc_info.value.message.lower()

    def test_buy_quantity_negative_raises(self, transaction_service, account_for_transactions):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            quantity=Decimal("-1"),
        )
        with pytest.raises(ValidationError):
            transaction_service.create_transaction(txn)

    def test_buy_price_negative_raises(self, transaction_service, account_for_transactions):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            price=Decimal("-0.01"),
        )
        with pytest.raises(ValidationError) as exc_info:
            transaction_service.create_transaction(txn)
        assert "price" in exc_info.value.message.lower()

    def test_buy_fees_negative_raises(self, transaction_service, account_for_transactions):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            fees=Decimal("-1"),
        )
        with pytest.raises(ValidationError) as exc_info:
            transaction_service.create_transaction(txn)
        assert "fee" in exc_info.value.message.lower()

    def test_buy_valid_succeeds(self, transaction_service, account_for_transactions):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("150.00"),
            fees=Decimal("1.50"),
            txn_id="buy-1",
        )
        transaction_service.create_transaction(txn)
        out = transaction_service.get_transaction("buy-1")
        assert out["txn_type"] == "BUY"
        assert out["symbol"] == "AAPL"

    def test_buy_symbol_normalized_to_uppercase(self, transaction_service, account_for_transactions):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            symbol="aapl",
            quantity=Decimal("10"),
            price=Decimal("150.00"),
            txn_id="sym-norm-1",
        )
        transaction_service.create_transaction(txn)
        out = transaction_service.get_transaction("sym-norm-1")
        assert out["symbol"] == "AAPL"

    def test_sell_missing_symbol_raises(self, transaction_service, account_for_transactions):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.SELL,
            symbol=None,
        )
        with pytest.raises(ValidationError) as exc_info:
            transaction_service.create_transaction(txn)
        assert "symbol" in exc_info.value.message.lower()

    def test_sell_valid_succeeds(self, transaction_service, account_for_transactions):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.SELL,
            symbol="MSFT",
            quantity=Decimal("5"),
            price=Decimal("400.00"),
            txn_id="sell-1",
        )
        transaction_service.create_transaction(txn)
        out = transaction_service.get_transaction("sell-1")
        assert out["txn_type"] == "SELL"
        assert out["symbol"] == "MSFT"


# -----------------------------------------------------------------------------
# _validate_transaction_create: CASH_DEPOSIT / CASH_WITHDRAW
# -----------------------------------------------------------------------------

class TestValidateTransactionCreateCash:
    """Validation for CASH_DEPOSIT and CASH_WITHDRAW: cash_amount > 0."""

    def test_cash_deposit_missing_cash_amount_raises(
        self, transaction_service, account_for_transactions
    ):
        # Build manually so cash_amount stays None (helper would default it)
        txn = TransactionCreate(
            account_name=account_for_transactions,
            txn_type=TransactionType.CASH_DEPOSIT,
            txn_time_est=datetime(2025, 1, 15, 12, 0, 0),
            symbol=None,
            quantity=None,
            price=None,
            cash_amount=None,
            fees=Decimal("0"),
            note=None,
            txn_id=None,
        )
        with pytest.raises(ValidationError) as exc_info:
            transaction_service.create_transaction(txn)
        assert "cash" in exc_info.value.message.lower()

    def test_cash_deposit_zero_cash_amount_raises(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("0"),
            symbol=None,
            quantity=None,
            price=None,
        )
        with pytest.raises(ValidationError):
            transaction_service.create_transaction(txn)

    def test_cash_deposit_negative_cash_amount_raises(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("-100"),
            symbol=None,
            quantity=None,
            price=None,
        )
        with pytest.raises(ValidationError):
            transaction_service.create_transaction(txn)

    def test_cash_deposit_valid_succeeds(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("5000.00"),
            symbol=None,
            quantity=None,
            price=None,
            txn_id="dep-1",
        )
        transaction_service.create_transaction(txn)
        out = transaction_service.get_transaction("dep-1")
        assert out["txn_type"] == "CASH_DEPOSIT"
        assert float(out["cash_amount"]) == 5000.0

    def test_cash_withdraw_valid_succeeds(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.CASH_WITHDRAW,
            cash_amount=Decimal("1000.00"),
            symbol=None,
            quantity=None,
            price=None,
            txn_id="with-1",
        )
        transaction_service.create_transaction(txn)
        out = transaction_service.get_transaction("with-1")
        assert out["txn_type"] == "CASH_WITHDRAW"
        assert float(out["cash_amount"]) == 1000.0


# -----------------------------------------------------------------------------
# _validate_transaction_create: txn_time_est required
# -----------------------------------------------------------------------------

class TestValidateTransactionCreateTime:
    """txn_time_est is required."""

    def test_txn_time_est_none_raises(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("100"),
            symbol=None,
            quantity=None,
            price=None,
        )
        txn.txn_time_est = None
        with pytest.raises(ValidationError) as exc_info:
            transaction_service.create_transaction(txn)
        assert "txn_time_est" in exc_info.value.message.lower() or "required" in exc_info.value.message.lower()


# -----------------------------------------------------------------------------
# create_transaction: auto txn_id
# -----------------------------------------------------------------------------

class TestCreateTransactionAutoId:
    """Create with and without explicit txn_id."""

    def test_create_without_txn_id_gets_hex_id(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            txn_id=None,
        )
        transaction_service.create_transaction(txn)
        # Should be persisted with a generated id; we can list or check DB
        import sqlite3
        conn = sqlite3.connect(transaction_service._transaction_db_path)
        cur = conn.cursor()
        cur.execute("SELECT txn_id FROM transactions")
        rows = cur.fetchall()
        conn.close()
        assert len(rows) == 1
        assert len(rows[0][0]) == 32  # uuid4 hex

    def test_create_with_txn_id_uses_it(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            txn_id="my-custom-id-123",
        )
        transaction_service.create_transaction(txn)
        out = transaction_service.get_transaction("my-custom-id-123")
        assert out["txn_id"] == "my-custom-id-123"


# -----------------------------------------------------------------------------
# create_batch_transaction
# -----------------------------------------------------------------------------

class TestCreateBatchTransaction:
    """Batch create: empty, multiple, one invalid."""

    def test_create_batch_empty_list(self, transaction_service, account_for_transactions):
        transaction_service.create_batch_transaction([])
        import sqlite3
        conn = sqlite3.connect(transaction_service._transaction_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions")
        assert cur.fetchone()[0] == 0
        conn.close()

    def test_create_batch_multiple_success(
        self, transaction_service, account_for_transactions
    ):
        txns = [
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                txn_id="batch-1",
            ),
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("200"),
                symbol=None,
                quantity=None,
                price=None,
                txn_id="batch-2",
            ),
        ]
        transaction_service.create_batch_transaction(txns)
        assert transaction_service.get_transaction("batch-1")["txn_id"] == "batch-1"
        assert transaction_service.get_transaction("batch-2")["txn_id"] == "batch-2"

    def test_create_batch_one_invalid_raises(
        self, transaction_service, account_for_transactions
    ):
        txns = [
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                txn_id="batch-ok",
            ),
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                quantity=Decimal("-1"),
                txn_id="batch-bad",
            ),
        ]
        with pytest.raises(ValidationError):
            transaction_service.create_batch_transaction(txns)
        # First may be committed (current impl validates then saves each)
        # So batch-ok might exist
        import sqlite3
        conn = sqlite3.connect(transaction_service._transaction_db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM transactions")
        n = cur.fetchone()[0]
        conn.close()
        assert n in (0, 1)


# -----------------------------------------------------------------------------
# get_transaction
# -----------------------------------------------------------------------------

class TestGetTransaction:
    """get_transaction: found vs not found."""

    def test_get_transaction_found(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            txn_id="get-me",
        )
        transaction_service.create_transaction(txn)
        out = transaction_service.get_transaction("get-me")
        assert out["txn_id"] == "get-me"
        assert out["account_name"] == account_for_transactions
        assert out["txn_type"] == "BUY"

    def test_get_transaction_not_found_raises(self, transaction_service):
        with pytest.raises(NotFoundError) as exc_info:
            transaction_service.get_transaction("no-such-id")
        assert "Transaction" in exc_info.value.message
        assert "no-such-id" in exc_info.value.message


# -----------------------------------------------------------------------------
# list_transactions
# -----------------------------------------------------------------------------

class TestListTransactions:
    """list_transactions: filter by list of accounts; return all matching transactions."""

    def test_list_transactions_empty_returns_empty_list(
        self, transaction_service, account_for_transactions
    ):
        rows = transaction_service.list_transactions(account_names=None)
        assert rows == []

    def test_list_transactions_all_accounts_no_filter(
        self, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_id="list-1",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_id="list-2",
            )
        )
        rows = transaction_service.list_transactions(account_names=None)
        assert len(rows) == 2
        txn_ids = {r["txn_id"] for r in rows}
        assert txn_ids == {"list-1", "list-2"}

    def test_list_transactions_filter_by_single_account(
        self, transaction_service, account_service, account_for_transactions
    ):
        account_service.save_account(AccountCreate(name="OtherBroker"))
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_id="acc1-txn",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name="OtherBroker",
                txn_id="acc2-txn",
            )
        )
        rows = transaction_service.list_transactions(
            account_names=[account_for_transactions]
        )
        assert len(rows) == 1
        assert rows[0]["txn_id"] == "acc1-txn"
        assert rows[0]["account_name"] == account_for_transactions

    def test_list_transactions_filter_by_list_of_accounts(
        self, transaction_service, account_service, account_for_transactions
    ):
        account_service.save_account(AccountCreate(name="BrokerA"))
        account_service.save_account(AccountCreate(name="BrokerB"))
        account_service.save_account(AccountCreate(name="BrokerC"))
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_id="t1",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name="BrokerA",
                txn_id="t2",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name="BrokerB",
                txn_id="t3",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name="BrokerC",
                txn_id="t4",
            )
        )
        rows = transaction_service.list_transactions(
            account_names=["BrokerA", "BrokerB"]
        )
        assert len(rows) == 2
        txn_ids = {r["txn_id"] for r in rows}
        assert txn_ids == {"t2", "t3"}

    def test_list_transactions_empty_list_returns_all(
        self, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_id="only-one",
            )
        )
        rows = transaction_service.list_transactions(account_names=[])
        assert len(rows) == 1
        assert rows[0]["txn_id"] == "only-one"

    def test_list_transactions_returns_dicts_same_shape_as_get_transaction(
        self, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_id="shape-1",
            )
        )
        rows = transaction_service.list_transactions(account_names=None)
        one = transaction_service.get_transaction("shape-1")
        assert set(rows[0].keys()) == set(one.keys())
        assert rows[0]["txn_id"] == one["txn_id"]


# -----------------------------------------------------------------------------
# _row_to_transaction_create (used by edit_transaction)
# -----------------------------------------------------------------------------

class TestRowToTransactionCreate:
    """_row_to_transaction_create: valid row and missing txn_time_est."""

    def test_row_to_transaction_create_valid_row(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            txn_id="row-test",
        )
        transaction_service.create_transaction(txn)
        row = transaction_service.get_transaction("row-test")
        txn_create = transaction_service._row_to_transaction_create(row)
        assert txn_create.txn_id == "row-test"
        assert txn_create.account_name == account_for_transactions
        assert txn_create.txn_type == TransactionType.BUY
        assert txn_create.symbol == "AAPL"
        assert txn_create.quantity == Decimal("10")
        assert txn_create.price == Decimal("150.50")

    def test_row_to_transaction_create_missing_txn_time_est_raises(
        self, transaction_service
    ):
        row = {
            "txn_id": "x",
            "account_name": "A",
            "txn_type": "BUY",
            "txn_time_est": None,
            "symbol": "AAPL",
            "quantity": 10,
            "price": 150,
            "cash_amount": None,
            "fees": 0,
            "note": None,
        }
        with pytest.raises(ValidationError) as exc_info:
            transaction_service._row_to_transaction_create(row)
        assert "txn_time_est" in exc_info.value.message.lower() or "required" in exc_info.value.message.lower()


# -----------------------------------------------------------------------------
# edit_transaction
# -----------------------------------------------------------------------------

class TestEditTransaction:
    """edit_transaction: change fields, not found."""

    def test_edit_transaction_change_note(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            txn_id="edit-note",
            note="Original",
        )
        transaction_service.create_transaction(txn)
        edited = transaction_service.edit_transaction(
            TransactionEdit(txn_id="edit-note", note="Updated note")
        )
        assert edited["note"] == "Updated note"
        assert edited["txn_id"] == "edit-note"

    def test_edit_transaction_change_symbol_quantity_price(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("150"),
            txn_id="edit-fields",
        )
        transaction_service.create_transaction(txn)
        edited = transaction_service.edit_transaction(
            TransactionEdit(
                txn_id="edit-fields",
                symbol="MSFT",
                quantity=Decimal("20"),
                price=Decimal("400"),
            )
        )
        assert edited["symbol"] == "MSFT"
        assert float(edited["quantity"]) == 20
        assert float(edited["price"]) == 400

    def test_edit_transaction_symbol_normalized_to_uppercase(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            txn_id="edit-sym-norm",
        )
        transaction_service.create_transaction(txn)
        edited = transaction_service.edit_transaction(
            TransactionEdit(txn_id="edit-sym-norm", symbol="msft")
        )
        assert edited["symbol"] == "MSFT"

    def test_edit_transaction_change_account(
        self, transaction_service, account_service, account_for_transactions
    ):
        account_service.save_account(AccountCreate(name="OtherBroker"))
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            txn_id="edit-acc",
        )
        transaction_service.create_transaction(txn)
        edited = transaction_service.edit_transaction(
            TransactionEdit(txn_id="edit-acc", account_name="OtherBroker")
        )
        assert edited["account_name"] == "OtherBroker"

    def test_edit_transaction_change_type_to_cash(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            txn_id="edit-type",
        )
        transaction_service.create_transaction(txn)
        edited = transaction_service.edit_transaction(
            TransactionEdit(
                txn_id="edit-type",
                txn_type=TransactionType.CASH_DEPOSIT,
                symbol=None,
                quantity=None,
                price=None,
                cash_amount=Decimal("999"),
            )
        )
        assert edited["txn_type"] == "CASH_DEPOSIT"
        assert float(edited["cash_amount"]) == 999

    def test_edit_transaction_not_found_raises(self, transaction_service):
        with pytest.raises(NotFoundError):
            transaction_service.edit_transaction(
                TransactionEdit(txn_id="no-such-id", note="x")
            )


# -----------------------------------------------------------------------------
# delete_transaction
# -----------------------------------------------------------------------------

class TestDeleteTransaction:
    """delete_transaction: success and idempotent."""

    def test_delete_transaction_success(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            txn_id="del-me",
        )
        transaction_service.create_transaction(txn)
        transaction_service.delete_transaction("del-me")
        with pytest.raises(NotFoundError):
            transaction_service.get_transaction("del-me")

    def test_delete_transaction_nonexistent_no_error(self, transaction_service):
        transaction_service.delete_transaction("no-such-id")

    def test_delete_then_create_same_id(
        self, transaction_service, account_for_transactions
    ):
        txn = make_transaction_create(
            account_name=account_for_transactions,
            txn_type=TransactionType.BUY,
            txn_id="reuse-id",
        )
        transaction_service.create_transaction(txn)
        transaction_service.delete_transaction("reuse-id")
        transaction_service.create_transaction(txn)
        out = transaction_service.get_transaction("reuse-id")
        assert out["txn_id"] == "reuse-id"
