"""Placeholder tests to verify scaffold works."""

from decimal import Decimal

import pytest

from app.domain.models import (
    Account,
    Transaction,
    TransactionType,
    CostBasisMethod,
)
from app.services import TransactionCreate


class TestDomainModels:
    """Test domain model creation."""

    def test_create_account(self):
        """Test Account model instantiation."""
        account = Account(
            account_id="test-123",
            name="Test Account",
            cost_basis_method=CostBasisMethod.FIFO,
        )
        assert account.account_id == "test-123"
        assert account.name == "Test Account"
        assert account.cost_basis_method == CostBasisMethod.FIFO

    def test_create_buy_transaction(self):
        """Test BUY Transaction model instantiation."""
        txn = Transaction(
            txn_id="txn-123",
            account_id="acc-123",
            txn_time_est=None,
            txn_type=TransactionType.BUY,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("150.00"),
            fees=Decimal("0"),
        )
        assert txn.is_stock_transaction
        assert not txn.is_cash_transaction
        # BUY reduces cash: -(10 * 150 + 0) = -1500
        assert txn.net_cash_impact == Decimal("-1500.00")

    def test_create_cash_deposit_transaction(self):
        """Test CASH_DEPOSIT Transaction model instantiation."""
        txn = Transaction(
            txn_id="txn-456",
            account_id="acc-123",
            txn_time_est=None,
            txn_type=TransactionType.CASH_DEPOSIT,
            cash_amount=Decimal("10000.00"),
        )
        assert txn.is_cash_transaction
        assert not txn.is_stock_transaction
        assert txn.net_cash_impact == Decimal("10000.00")


class TestLedgerService:
    """Test LedgerService operations."""

    def test_create_account(self, ledger_service):
        """Test account creation via service."""
        account = ledger_service.create_account("My Brokerage")
        assert account.name == "My Brokerage"
        assert account.cost_basis_method == CostBasisMethod.FIFO
        assert account.account_id is not None

    def test_add_buy_transaction(self, ledger_service):
        """Test adding a BUY transaction."""
        account = ledger_service.create_account("Test Account")

        txn = ledger_service.add_transaction(
            TransactionCreate(
                account_id=account.account_id,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("185.50"),
            )
        )

        assert txn.symbol == "AAPL"
        assert txn.quantity == Decimal("10")
        assert txn.price == Decimal("185.50")


class TestPortfolioEngine:
    """Test PortfolioEngine operations."""

    def test_rebuild_account_with_transactions(
        self,
        ledger_service,
        portfolio_engine,
    ):
        """Test portfolio rebuild after transactions."""
        account = ledger_service.create_account("Portfolio Test")

        # Add cash deposit
        ledger_service.add_transaction(
            TransactionCreate(
                account_id=account.account_id,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000.00"),
            )
        )

        # Add buy
        ledger_service.add_transaction(
            TransactionCreate(
                account_id=account.account_id,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("185.50"),
            )
        )

        # Rebuild and verify
        portfolio_engine.rebuild_account(account.account_id)

        positions = portfolio_engine.get_positions(account.account_id)
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].shares == Decimal("10")

        cash = portfolio_engine.get_cash_balance(account.account_id)
        # 10000 - (10 * 185.50) = 10000 - 1855 = 8145
        assert cash == Decimal("8145.00")


class TestMarketDataService:
    """Test MarketDataService operations."""

    def test_get_quotes(self, market_data_service):
        """Test fetching quotes from deterministic provider."""
        quotes = market_data_service.get_quotes(["AAPL", "GOOGL"])

        assert "AAPL" in quotes
        assert "GOOGL" in quotes
        assert quotes["AAPL"].last_price == Decimal("185.50")
        assert quotes["AAPL"].prev_close == Decimal("184.25")


class TestAPIEndpoints:
    """Test FastAPI endpoints."""

    def test_health_check(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_create_account_endpoint(self, client):
        """Test account creation endpoint."""
        response = client.post(
            "/accounts/",
            json={"name": "API Test Account"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "API Test Account"
        assert "account_id" in data

    def test_list_accounts_endpoint(self, client):
        """Test account listing endpoint."""
        # Create an account first
        client.post("/accounts/", json={"name": "List Test"})

        response = client.get("/accounts/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1


class TestAppContext:
    """Test AppContext for desktop app."""

    def test_app_context_initialization(self, tmp_path):
        """Test AppContext initializes correctly with custom data_dir."""
        from app.app_context import AppContext

        data_dir = tmp_path / "test_data"
        ctx = AppContext(data_dir=data_dir)
        ctx.initialize()

        assert ctx.is_initialized
        assert ctx.data_dir == data_dir
        assert (data_dir / "investment.db").exists()

        # Test services are accessible
        assert ctx.ledger is not None
        assert ctx.portfolio is not None
        assert ctx.market_data is not None
        assert ctx.analysis is not None

        ctx.close()

    def test_app_context_creates_account(self, tmp_path):
        """Test creating account through AppContext."""
        from app.app_context import AppContext

        data_dir = tmp_path / "test_data2"
        ctx = AppContext(data_dir=data_dir)
        ctx.initialize()

        # Create account
        account = ctx.ledger.create_account("Test Account")
        assert account.name == "Test Account"

        # Verify it's in the list
        accounts = ctx.ledger.list_accounts()
        assert len(accounts) == 1
        assert accounts[0].name == "Test Account"

        ctx.close()
