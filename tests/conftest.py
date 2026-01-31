"""
Pytest configuration and fixtures for investment tracking app tests.

This module provides:
- In-memory SQLite database fixtures
- Factory helpers for accounts and transactions
- Deterministic stub market data providers
- Time helpers for Eastern timezone
- Service and repository fixtures
"""

import os
import tempfile
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable, Optional
from unittest.mock import MagicMock

import pytest
import pytz
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.sqlalchemy.database import Base, get_db
# Import ORM models to register them with Base before creating tables
from app.repositories.sqlalchemy import orm_models  # noqa: F401
from app.repositories.sqlalchemy import (
    SqlAlchemyAccountRepository,
    SqlAlchemyTransactionRepository,
    SqlAlchemyCacheRepository,
)
from app.providers.stub_provider import StubMarketDataProvider
from app.providers.market_data_provider import MarketDataProvider
from app.services import (
    LedgerService,
    PortfolioEngine,
    MarketDataService,
    AnalysisService,
)
from app.services.ledger_service import TransactionCreate, TransactionUpdate
from app.csv import CsvImporter, CsvExporter, CsvTemplateGenerator
from app.domain.models import (
    Account,
    Transaction,
    TransactionType,
    CostBasisMethod,
    PositionCache,
    CashCache,
)
from app.domain.views import Quote
from app.core.timezone import EASTERN_TZ
from app.config.settings import reset_settings


# =============================================================================
# TIMEZONE HELPERS
# =============================================================================


def eastern_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 10,
    minute: int = 0,
    second: int = 0,
) -> datetime:
    """Create a localized datetime in US/Eastern timezone."""
    return EASTERN_TZ.localize(datetime(year, month, day, hour, minute, second))


@pytest.fixture
def fixed_now() -> datetime:
    """Fixed 'now' timestamp for deterministic tests."""
    return eastern_datetime(2024, 6, 15, 14, 30, 0)


# =============================================================================
# DATABASE FIXTURES
# =============================================================================


@pytest.fixture(scope="function")
def test_engine():
    """Create test database engine with shared in-memory SQLite."""
    # Reset settings for clean state
    reset_settings()

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_session(test_engine) -> Session:
    """Create test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


# =============================================================================
# REPOSITORY FIXTURES
# =============================================================================


@pytest.fixture
def account_repo(test_session) -> SqlAlchemyAccountRepository:
    """Provide test AccountRepository."""
    return SqlAlchemyAccountRepository(test_session)


@pytest.fixture
def transaction_repo(test_session) -> SqlAlchemyTransactionRepository:
    """Provide test TransactionRepository."""
    return SqlAlchemyTransactionRepository(test_session)


@pytest.fixture
def cache_repo(test_session) -> SqlAlchemyCacheRepository:
    """Provide test CacheRepository."""
    return SqlAlchemyCacheRepository(test_session)


# =============================================================================
# MARKET DATA FIXTURES
# =============================================================================


class DeterministicMarketProvider:
    """
    Deterministic market data provider for testing.
    
    Provides fixed quotes with no randomness.
    """
    
    FIXED_QUOTES = {
        "AAPL": (Decimal("185.50"), Decimal("184.25")),  # +1.25 / +0.68%
        "GOOGL": (Decimal("142.75"), Decimal("141.50")),  # +1.25 / +0.88%
        "MSFT": (Decimal("378.25"), Decimal("376.80")),  # +1.45 / +0.38%
        "TSLA": (Decimal("248.75"), Decimal("250.10")),  # -1.35 / -0.54% (down)
        "SPY": (Decimal("485.25"), Decimal("484.10")),  # +1.15 / +0.24%
    }
    
    def __init__(self, as_of: Optional[datetime] = None):
        self._as_of = as_of or eastern_datetime(2024, 6, 15, 16, 0, 0)
    
    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        """Return deterministic quotes for requested symbols."""
        result = {}
        for symbol in symbols:
            upper_symbol = symbol.upper()
            if upper_symbol in self.FIXED_QUOTES:
                last_price, prev_close = self.FIXED_QUOTES[upper_symbol]
                result[upper_symbol] = Quote(
                    symbol=upper_symbol,
                    last_price=last_price,
                    prev_close=prev_close,
                    as_of=self._as_of,
                )
        return result
    
    def is_trading_day(self) -> bool:
        return True
    
    def previous_trading_day(self) -> str:
        return "2024-06-14"


class FailingMarketProvider:
    """Market provider that always raises an exception."""
    
    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        raise ConnectionError("Network unavailable")
    
    def is_trading_day(self) -> bool:
        raise ConnectionError("Network unavailable")
    
    def previous_trading_day(self) -> str:
        raise ConnectionError("Network unavailable")


class FallbackChainProvider:
    """Market provider with configurable fallback behavior."""
    
    def __init__(
        self,
        primary: MarketDataProvider,
        fallback: MarketDataProvider,
    ):
        self._primary = primary
        self._fallback = fallback
    
    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        try:
            return self._primary.get_quotes(symbols)
        except Exception:
            return self._fallback.get_quotes(symbols)
    
    def is_trading_day(self) -> bool:
        try:
            return self._primary.is_trading_day()
        except Exception:
            return self._fallback.is_trading_day()
    
    def previous_trading_day(self) -> str:
        try:
            return self._primary.previous_trading_day()
        except Exception:
            return self._fallback.previous_trading_day()


@pytest.fixture
def deterministic_provider(fixed_now) -> DeterministicMarketProvider:
    """Provide deterministic market data provider."""
    return DeterministicMarketProvider(as_of=fixed_now)


@pytest.fixture
def failing_provider() -> FailingMarketProvider:
    """Provide a market provider that always fails."""
    return FailingMarketProvider()


@pytest.fixture
def market_provider() -> StubMarketDataProvider:
    """Provide test MarketDataProvider with fixed seed."""
    return StubMarketDataProvider(seed=42)


# =============================================================================
# SERVICE FIXTURES
# =============================================================================


@pytest.fixture
def ledger_service(account_repo, transaction_repo) -> LedgerService:
    """Provide test LedgerService."""
    return LedgerService(
        account_repo=account_repo,
        transaction_repo=transaction_repo,
    )


@pytest.fixture
def portfolio_engine(account_repo, transaction_repo, cache_repo) -> PortfolioEngine:
    """Provide test PortfolioEngine."""
    return PortfolioEngine(
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        cache_repo=cache_repo,
    )


@pytest.fixture
def market_data_service(deterministic_provider) -> MarketDataService:
    """Provide test MarketDataService with deterministic provider."""
    return MarketDataService(
        provider=deterministic_provider,
        cache_ttl_seconds=60,
    )


@pytest.fixture
def analysis_service(portfolio_engine, market_data_service) -> AnalysisService:
    """Provide test AnalysisService."""
    return AnalysisService(
        portfolio_engine=portfolio_engine,
        market_data_service=market_data_service,
    )


@pytest.fixture
def csv_importer(ledger_service, portfolio_engine) -> CsvImporter:
    """Provide test CsvImporter."""
    return CsvImporter(
        ledger_service=ledger_service,
        portfolio_engine=portfolio_engine,
    )


@pytest.fixture
def csv_exporter(ledger_service) -> CsvExporter:
    """Provide test CsvExporter."""
    return CsvExporter(ledger_service=ledger_service)


@pytest.fixture
def csv_template_generator() -> CsvTemplateGenerator:
    """Provide test CsvTemplateGenerator."""
    return CsvTemplateGenerator()


# =============================================================================
# FACTORY FIXTURES
# =============================================================================


@pytest.fixture
def account_factory(ledger_service) -> Callable[..., Account]:
    """Factory for creating test accounts."""
    
    def _create_account(
        name: Optional[str] = None,
        cost_basis_method: str = "FIFO",
    ) -> Account:
        if name is None:
            name = f"Test Account {uuid.uuid4().hex[:8]}"
        return ledger_service.create_account(
            name=name,
            cost_basis_method=cost_basis_method,
        )
    
    return _create_account


@pytest.fixture
def transaction_factory(
    ledger_service,
    portfolio_engine,
) -> Callable[..., Transaction]:
    """Factory for creating test transactions with auto-rebuild."""
    
    def _create_transaction(
        account_id: str,
        txn_type: TransactionType,
        symbol: Optional[str] = None,
        quantity: Optional[Decimal] = None,
        price: Optional[Decimal] = None,
        cash_amount: Optional[Decimal] = None,
        fees: Decimal = Decimal("0"),
        note: Optional[str] = None,
        txn_time_est: Optional[datetime] = None,
        rebuild: bool = True,
    ) -> Transaction:
        data = TransactionCreate(
            account_id=account_id,
            txn_type=txn_type,
            symbol=symbol,
            quantity=quantity,
            price=price,
            cash_amount=cash_amount,
            fees=fees,
            note=note,
            txn_time_est=txn_time_est,
        )
        txn = ledger_service.add_transaction(data)
        if rebuild:
            portfolio_engine.rebuild_account(account_id)
        return txn
    
    return _create_transaction


# =============================================================================
# PRESET DATA FIXTURES
# =============================================================================


@pytest.fixture
def sample_account(account_factory) -> Account:
    """Create a sample account."""
    return account_factory(name="Brokerage")


@pytest.fixture
def sample_account_with_cash(
    sample_account,
    transaction_factory,
    portfolio_engine,
) -> tuple[Account, Decimal]:
    """Create a sample account with $10,000 cash deposit."""
    cash_amount = Decimal("10000.00")
    transaction_factory(
        account_id=sample_account.account_id,
        txn_type=TransactionType.CASH_DEPOSIT,
        cash_amount=cash_amount,
    )
    return sample_account, cash_amount


@pytest.fixture
def sample_account_with_positions(
    sample_account_with_cash,
    transaction_factory,
) -> tuple[Account, dict]:
    """Create a sample account with positions and cash."""
    account, initial_cash = sample_account_with_cash
    
    # Buy 10 AAPL @ $185.00
    transaction_factory(
        account_id=account.account_id,
        txn_type=TransactionType.BUY,
        symbol="AAPL",
        quantity=Decimal("10"),
        price=Decimal("185.00"),
        fees=Decimal("0"),
    )
    
    # Buy 5 MSFT @ $375.00
    transaction_factory(
        account_id=account.account_id,
        txn_type=TransactionType.BUY,
        symbol="MSFT",
        quantity=Decimal("5"),
        price=Decimal("375.00"),
        fees=Decimal("0"),
    )
    
    expected = {
        "AAPL": Decimal("10"),
        "MSFT": Decimal("5"),
        "cash": initial_cash - Decimal("1850.00") - Decimal("1875.00"),  # 6275.00
    }
    
    return account, expected


# =============================================================================
# API TEST CLIENT FIXTURE
# =============================================================================


@pytest.fixture
def client(test_engine) -> TestClient:
    """Provide FastAPI test client with test database."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# =============================================================================
# TEMP FILE FIXTURES
# =============================================================================


@pytest.fixture
def temp_csv_file():
    """Provide a temporary CSV file path that is cleaned up after test."""
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        encoding="utf-8",
    ) as f:
        tmp_path = f.name
    
    yield tmp_path
    
    # Cleanup
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture
def sample_csv_content() -> str:
    """Sample valid CSV content for import testing."""
    return """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
Brokerage,2024-01-15 10:30:00,CASH_DEPOSIT,,,,,0,Initial deposit
Brokerage,2024-01-15 14:00:00,BUY,AAPL,10,185.50,,0,Initial position
Brokerage,2024-02-01 11:00:00,BUY,MSFT,5,375.00,,4.95,Added MSFT
"""


@pytest.fixture
def invalid_csv_content() -> str:
    """Sample CSV content with errors for testing error handling."""
    return """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
Brokerage,2024-01-15 10:30:00,CASH_DEPOSIT,,,,10000,0,Valid deposit
Brokerage,2024-01-15 14:00:00,INVALID_TYPE,AAPL,10,185.50,,0,Invalid type
Brokerage,2024-02-01 11:00:00,BUY,AAPL,not_a_number,185.50,,0,Invalid quantity
,2024-02-01 12:00:00,BUY,AAPL,10,185.50,,0,Missing account
"""


# =============================================================================
# HELPER FUNCTIONS (exported for use in tests)
# =============================================================================


def assert_decimal_equal(
    actual: Decimal,
    expected: Decimal,
    tolerance: Decimal = Decimal("0.01"),
) -> None:
    """Assert two Decimals are equal within tolerance."""
    diff = abs(actual - expected)
    assert diff <= tolerance, f"Expected {expected}, got {actual} (diff={diff})"


def create_buy_transaction_data(
    account_id: str,
    symbol: str,
    quantity: Decimal,
    price: Decimal,
    fees: Decimal = Decimal("0"),
    txn_time_est: Optional[datetime] = None,
) -> TransactionCreate:
    """Helper to create BUY transaction data."""
    return TransactionCreate(
        account_id=account_id,
        txn_type=TransactionType.BUY,
        symbol=symbol,
        quantity=quantity,
        price=price,
        fees=fees,
        txn_time_est=txn_time_est,
    )


def create_sell_transaction_data(
    account_id: str,
    symbol: str,
    quantity: Decimal,
    price: Decimal,
    fees: Decimal = Decimal("0"),
    txn_time_est: Optional[datetime] = None,
) -> TransactionCreate:
    """Helper to create SELL transaction data."""
    return TransactionCreate(
        account_id=account_id,
        txn_type=TransactionType.SELL,
        symbol=symbol,
        quantity=quantity,
        price=price,
        fees=fees,
        txn_time_est=txn_time_est,
    )


def create_cash_deposit_data(
    account_id: str,
    amount: Decimal,
    txn_time_est: Optional[datetime] = None,
) -> TransactionCreate:
    """Helper to create CASH_DEPOSIT transaction data."""
    return TransactionCreate(
        account_id=account_id,
        txn_type=TransactionType.CASH_DEPOSIT,
        cash_amount=amount,
        txn_time_est=txn_time_est,
    )


def create_cash_withdraw_data(
    account_id: str,
    amount: Decimal,
    txn_time_est: Optional[datetime] = None,
) -> TransactionCreate:
    """Helper to create CASH_WITHDRAW transaction data."""
    return TransactionCreate(
        account_id=account_id,
        txn_type=TransactionType.CASH_WITHDRAW,
        cash_amount=amount,
        txn_time_est=txn_time_est,
    )
