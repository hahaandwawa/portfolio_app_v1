"""
Pytest fixtures for service tests.
Provides isolated test DBs under src/tests/.test_cache and schema creation.
"""
from pathlib import Path
import sqlite3
import tempfile
import shutil

import pytest

from src.service.account_service import AccountService, AccountCreate
from src.service.transaction_service import (
    TransactionService,
    TransactionCreate,
    TransactionEdit,
)
from src.service.enums import TransactionType
from src.utils.exceptions import NotFoundError


# Test cache directory under src/tests
TESTS_DIR = Path(__file__).resolve().parent
TEST_CACHE = TESTS_DIR / ".test_cache"


def _ensure_test_cache():
    TEST_CACHE.mkdir(parents=True, exist_ok=True)
    return TEST_CACHE


def _create_accounts_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            name TEXT NOT NULL PRIMARY KEY
        )
        """
    )
    conn.commit()


def _create_transactions_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            txn_id TEXT NOT NULL PRIMARY KEY,
            account_name TEXT NOT NULL,
            txn_type TEXT NOT NULL,
            txn_time_est TEXT NOT NULL,
            symbol TEXT,
            quantity REAL,
            price REAL,
            cash_amount REAL,
            fees REAL,
            note TEXT,
            cash_destination_account TEXT
        )
        """
    )
    conn.commit()


def _create_historical_prices_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS historical_prices (
            symbol TEXT NOT NULL,
            date TEXT NOT NULL,
            close_price REAL NOT NULL,
            adj_close_price REAL,
            price_type TEXT NOT NULL DEFAULT 'close',
            updated_at TEXT NOT NULL,
            PRIMARY KEY (symbol, date)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_historical_prices_symbol_date ON historical_prices(symbol, date)"
    )
    conn.commit()


@pytest.fixture
def test_cache_dir():
    """Ensure test cache dir exists; yield path; optionally clean single-run DBs."""
    path = _ensure_test_cache()
    yield path


@pytest.fixture
def temp_db_dir(test_cache_dir):
    """Unique temp subdir under test cache for one test run (isolation)."""
    d = tempfile.mkdtemp(prefix="db_", dir=test_cache_dir)
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def account_db_path(temp_db_dir):
    """Path to a fresh accounts DB with schema."""
    path = temp_db_dir / "accounts.sqlite"
    conn = sqlite3.connect(str(path))
    _create_accounts_schema(conn)
    conn.close()
    return str(path)


@pytest.fixture
def transaction_db_path(temp_db_dir):
    """Path to a fresh transactions DB with schema."""
    path = temp_db_dir / "transactions.sqlite"
    conn = sqlite3.connect(str(path))
    _create_transactions_schema(conn)
    conn.close()
    return str(path)


@pytest.fixture
def account_service(account_db_path):
    """AccountService wired to test accounts DB."""
    return AccountService(account_db_path=account_db_path)


@pytest.fixture
def transaction_service(account_db_path, transaction_db_path):
    """TransactionService wired to test accounts + transactions DBs."""
    return TransactionService(
        transaction_db_path=transaction_db_path,
        account_db_path=account_db_path,
    )


@pytest.fixture
def historical_prices_db_path(temp_db_dir):
    """Path to a fresh historical_prices DB with schema."""
    path = temp_db_dir / "historical_prices.sqlite"
    conn = sqlite3.connect(str(path))
    _create_historical_prices_schema(conn)
    conn.close()
    return str(path)


@pytest.fixture
def transaction_service_with_validation(transaction_service, account_for_transactions):
    """TransactionService with symbol and sell validation (mock QuoteService + PortfolioService.get_quantity_held)."""
    from src.service.portfolio_service import PortfolioService

    class MockQuoteService:
        """Valid symbols: AAPL, MSFT, GOOG, NVDA, META, AMZN, TSLA. Others invalid."""

        def get_quotes(self, symbols):
            valid = {"AAPL", "MSFT", "GOOG", "NVDA", "META", "AMZN", "TSLA"}
            result = {}
            for sym in symbols:
                if sym in valid:
                    result[sym] = {"current_price": 100.0, "display_name": f"{sym} Inc."}
                else:
                    result[sym] = {"current_price": None, "display_name": sym}
            return result

    portfolio_service = PortfolioService(transaction_service=transaction_service)
    return TransactionService(
        transaction_db_path=transaction_service._transaction_db_path,
        account_db_path=transaction_service._account_db_path,
        quote_service=MockQuoteService(),
        get_quantity_held=portfolio_service.get_quantity_held,
    )


# ---------- Data builders for tests ----------

@pytest.fixture
def sample_account_create():
    """Default valid AccountCreate."""
    return AccountCreate(name="TestBroker")


@pytest.fixture
def account_for_transactions(account_service, sample_account_create):
    """Ensure one account exists for transaction tests."""
    try:
        account_service.get_account(sample_account_create.name)
    except NotFoundError:
        account_service.save_account(sample_account_create)
    return sample_account_create.name


def make_transaction_create(
    account_name: str = "TestBroker",
    txn_type: TransactionType = TransactionType.BUY,
    symbol: str = "AAPL",
    quantity=None,
    price=None,
    cash_amount=None,
    fees=None,
    note: str = None,
    txn_id: str = None,
    cash_destination_account: str = None,
    txn_time_est=None,
):
    """Build TransactionCreate; defaults for BUY; use cash_amount for CASH_*; txn_time_est optional."""
    from datetime import datetime
    from decimal import Decimal

    now = datetime(2025, 1, 15, 12, 0, 0) if txn_time_est is None else txn_time_est
    if quantity is None and txn_type in (TransactionType.BUY, TransactionType.SELL):
        quantity = Decimal("10")
    if price is None and txn_type in (TransactionType.BUY, TransactionType.SELL):
        price = Decimal("150.50")
    if cash_amount is None and txn_type in (
        TransactionType.CASH_DEPOSIT,
        TransactionType.CASH_WITHDRAW,
    ):
        cash_amount = Decimal("1000.00")
    if fees is None:
        fees = Decimal("0")

    return TransactionCreate(
        account_name=account_name,
        txn_type=txn_type,
        txn_time_est=now,
        symbol=symbol,
        quantity=quantity,
        price=price,
        cash_amount=cash_amount,
        fees=fees,
        note=note,
        txn_id=txn_id,
        cash_destination_account=cash_destination_account,
    )
