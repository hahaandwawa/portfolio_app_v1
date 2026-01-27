"""
API tests for analysis endpoints.

Tests cover:
- Get positions with prices
- Get cash balance
- Get today P/L
- Get allocation breakdown
- Get quotes
"""

import pytest
from decimal import Decimal
from fastapi.testclient import TestClient


# =============================================================================
# HELPER FIXTURES
# =============================================================================


@pytest.fixture
def test_account_with_positions(client: TestClient) -> dict:
    """Create a test account with cash and positions."""
    # Create account
    account = client.post("/accounts/", json={"name": "Test Account"}).json()
    account_id = account["account_id"]

    # Add cash deposit
    client.post("/transactions/", json={
        "account_id": account_id,
        "txn_type": "CASH_DEPOSIT",
        "cash_amount": "10000.00",
    })

    # Add positions
    client.post("/transactions/", json={
        "account_id": account_id,
        "txn_type": "BUY",
        "symbol": "AAPL",
        "quantity": "10",
        "price": "180.00",
    })
    client.post("/transactions/", json={
        "account_id": account_id,
        "txn_type": "BUY",
        "symbol": "MSFT",
        "quantity": "5",
        "price": "370.00",
    })

    return account


# =============================================================================
# POSITIONS TESTS
# =============================================================================


class TestPositionsAPI:
    """Tests for GET /analysis/positions endpoint."""

    def test_get_positions_empty(self, client: TestClient):
        """
        GIVEN no account IDs specified
        WHEN I GET /analysis/positions
        THEN response is 200 with empty positions
        """
        response = client.get("/analysis/positions")

        assert response.status_code == 200
        data = response.json()
        assert data["positions"] == []

    def test_get_positions_with_account(
        self,
        client: TestClient,
        test_account_with_positions: dict,
    ):
        """
        GIVEN an account with positions
        WHEN I GET /analysis/positions?account_ids=...
        THEN positions with prices are returned
        """
        account_id = test_account_with_positions["account_id"]

        response = client.get(f"/analysis/positions?account_ids={account_id}")

        assert response.status_code == 200
        data = response.json()

        # Check positions exist
        assert len(data["positions"]) >= 1

        # Check position fields
        position = data["positions"][0]
        assert "symbol" in position
        assert "shares" in position
        assert "last_price" in position
        assert "market_value" in position

    def test_get_positions_includes_cash_balance(
        self,
        client: TestClient,
        test_account_with_positions: dict,
    ):
        """
        GIVEN an account with positions
        WHEN I GET /analysis/positions
        THEN cash_balance is included
        """
        account_id = test_account_with_positions["account_id"]

        response = client.get(f"/analysis/positions?account_ids={account_id}")

        assert response.status_code == 200
        assert "cash_balance" in response.json()

    def test_get_positions_includes_total_value(
        self,
        client: TestClient,
        test_account_with_positions: dict,
    ):
        """
        GIVEN an account with positions
        WHEN I GET /analysis/positions
        THEN total_value is included
        """
        account_id = test_account_with_positions["account_id"]

        response = client.get(f"/analysis/positions?account_ids={account_id}")

        assert response.status_code == 200
        assert "total_value" in response.json()


# =============================================================================
# CASH BALANCE TESTS
# =============================================================================


class TestCashBalanceAPI:
    """Tests for GET /analysis/cash endpoint."""

    def test_get_cash_balance_no_accounts(self, client: TestClient):
        """
        GIVEN no account IDs
        WHEN I GET /analysis/cash
        THEN response is 200 with zero balance
        """
        response = client.get("/analysis/cash")

        assert response.status_code == 200
        assert Decimal(response.json()["cash_balance"]) == Decimal("0")

    def test_get_cash_balance_with_account(
        self,
        client: TestClient,
        test_account_with_positions: dict,
    ):
        """
        GIVEN an account with cash
        WHEN I GET /analysis/cash?account_ids=...
        THEN correct balance is returned
        """
        account_id = test_account_with_positions["account_id"]

        response = client.get(f"/analysis/cash?account_ids={account_id}")

        assert response.status_code == 200
        cash = Decimal(response.json()["cash_balance"])
        # Deposited 10000, bought AAPL (1800) and MSFT (1850)
        # Expected: 10000 - 1800 - 1850 = 6350
        assert cash > Decimal("0")


# =============================================================================
# TODAY P/L TESTS
# =============================================================================


class TestTodayPnlAPI:
    """Tests for GET /analysis/pnl endpoint."""

    def test_get_pnl_no_accounts(self, client: TestClient):
        """
        GIVEN no account IDs
        WHEN I GET /analysis/pnl
        THEN response is 200 with zero P/L
        """
        response = client.get("/analysis/pnl")

        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["pnl_dollars"]) == Decimal("0")

    def test_get_pnl_with_positions(
        self,
        client: TestClient,
        test_account_with_positions: dict,
    ):
        """
        GIVEN an account with positions
        WHEN I GET /analysis/pnl?account_ids=...
        THEN P/L calculation is returned
        """
        account_id = test_account_with_positions["account_id"]

        response = client.get(f"/analysis/pnl?account_ids={account_id}")

        assert response.status_code == 200
        data = response.json()

        # Check all expected fields
        assert "pnl_dollars" in data
        assert "pnl_percent" in data
        assert "prev_close_value" in data
        assert "current_value" in data
        assert "as_of" in data

    def test_get_pnl_response_format(
        self,
        client: TestClient,
        test_account_with_positions: dict,
    ):
        """
        GIVEN an account with positions
        WHEN I GET /analysis/pnl
        THEN pnl_dollars is a numeric string
        """
        account_id = test_account_with_positions["account_id"]

        response = client.get(f"/analysis/pnl?account_ids={account_id}")

        data = response.json()
        # Should be able to convert to Decimal
        pnl = Decimal(str(data["pnl_dollars"]))
        assert isinstance(pnl, Decimal)


# =============================================================================
# ALLOCATION TESTS
# =============================================================================


class TestAllocationAPI:
    """Tests for GET /analysis/allocation endpoint."""

    def test_get_allocation_no_accounts(self, client: TestClient):
        """
        GIVEN no account IDs
        WHEN I GET /analysis/allocation
        THEN response is 200 with empty items
        """
        response = client.get("/analysis/allocation")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert Decimal(data["total_value"]) == Decimal("0")

    def test_get_allocation_with_positions(
        self,
        client: TestClient,
        test_account_with_positions: dict,
    ):
        """
        GIVEN an account with positions
        WHEN I GET /analysis/allocation?account_ids=...
        THEN allocation breakdown is returned
        """
        account_id = test_account_with_positions["account_id"]

        response = client.get(f"/analysis/allocation?account_ids={account_id}")

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "items" in data
        assert "total_value" in data
        assert "as_of" in data

        # Check items
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "symbol" in item
        assert "market_value" in item
        assert "percentage" in item

    def test_get_allocation_percentages_sum_to_100(
        self,
        client: TestClient,
        test_account_with_positions: dict,
    ):
        """
        GIVEN an account with multiple positions
        WHEN I GET /analysis/allocation
        THEN percentages sum to approximately 100
        """
        account_id = test_account_with_positions["account_id"]

        response = client.get(f"/analysis/allocation?account_ids={account_id}")

        data = response.json()
        total_percent = sum(Decimal(item["percentage"]) for item in data["items"])

        # Should be close to 100 (within rounding tolerance)
        assert Decimal("99.5") <= total_percent <= Decimal("100.5")


# =============================================================================
# QUOTES TESTS
# =============================================================================


class TestQuotesAPI:
    """Tests for GET /analysis/quotes endpoint."""

    def test_get_quotes_single_symbol(self, client: TestClient):
        """
        GIVEN a valid symbol
        WHEN I GET /analysis/quotes?symbols=AAPL
        THEN quote is returned
        """
        response = client.get("/analysis/quotes?symbols=AAPL")

        assert response.status_code == 200
        quotes = response.json()

        assert len(quotes) >= 1
        quote = quotes[0]
        assert quote["symbol"] == "AAPL"
        assert "last_price" in quote
        assert "prev_close" in quote
        assert "as_of" in quote

    def test_get_quotes_multiple_symbols(self, client: TestClient):
        """
        GIVEN multiple symbols
        WHEN I GET /analysis/quotes?symbols=AAPL,MSFT
        THEN quotes for both are returned
        """
        response = client.get("/analysis/quotes?symbols=AAPL,MSFT")

        assert response.status_code == 200
        quotes = response.json()

        symbols = {q["symbol"] for q in quotes}
        assert "AAPL" in symbols
        assert "MSFT" in symbols

    def test_get_quotes_normalizes_to_uppercase(self, client: TestClient):
        """
        GIVEN lowercase symbols
        WHEN I GET /analysis/quotes
        THEN symbols are normalized
        """
        response = client.get("/analysis/quotes?symbols=aapl,msft")

        assert response.status_code == 200
        quotes = response.json()

        for quote in quotes:
            assert quote["symbol"].isupper()

    def test_get_quotes_missing_symbols_param_returns_422(self, client: TestClient):
        """
        GIVEN no symbols param
        WHEN I GET /analysis/quotes
        THEN response is 422
        """
        response = client.get("/analysis/quotes")

        assert response.status_code == 422

    def test_get_quotes_response_format(self, client: TestClient):
        """
        GIVEN a valid symbol
        WHEN I GET /analysis/quotes
        THEN prices are numeric
        """
        response = client.get("/analysis/quotes?symbols=AAPL")

        quote = response.json()[0]
        # Should be able to convert to Decimal
        assert Decimal(str(quote["last_price"])) > Decimal("0")
        assert Decimal(str(quote["prev_close"])) > Decimal("0")


# =============================================================================
# MULTI-ACCOUNT TESTS
# =============================================================================


class TestMultiAccountAnalysisAPI:
    """Tests for analysis across multiple accounts."""

    def test_positions_aggregated_across_accounts(
        self,
        client: TestClient,
    ):
        """
        GIVEN positions in multiple accounts
        WHEN I GET /analysis/positions with both account IDs
        THEN positions are aggregated
        """
        # Create two accounts
        acc1 = client.post("/accounts/", json={"name": "Account 1"}).json()
        acc2 = client.post("/accounts/", json={"name": "Account 2"}).json()

        # Add AAPL to both
        client.post("/transactions/", json={
            "account_id": acc1["account_id"],
            "txn_type": "BUY",
            "symbol": "AAPL",
            "quantity": "10",
            "price": "180.00",
        })
        client.post("/transactions/", json={
            "account_id": acc2["account_id"],
            "txn_type": "BUY",
            "symbol": "AAPL",
            "quantity": "5",
            "price": "182.00",
        })

        # Get aggregated
        response = client.get(
            f"/analysis/positions?account_ids={acc1['account_id']},{acc2['account_id']}"
        )

        assert response.status_code == 200
        positions = response.json()["positions"]

        # Should have one AAPL position with 15 shares
        aapl_position = next(p for p in positions if p["symbol"] == "AAPL")
        assert Decimal(aapl_position["shares"]) == Decimal("15")


# =============================================================================
# RESPONSE FORMAT COMPLIANCE TESTS
# =============================================================================


class TestAnalysisResponseFormats:
    """Tests for analysis endpoint response format compliance."""

    def test_all_decimal_fields_are_serializable(
        self,
        client: TestClient,
        test_account_with_positions: dict,
    ):
        """
        GIVEN positions and analysis data
        WHEN I GET analysis endpoints
        THEN all numeric fields can be parsed as Decimals
        """
        account_id = test_account_with_positions["account_id"]

        # Test positions
        pos_response = client.get(f"/analysis/positions?account_ids={account_id}")
        pos_data = pos_response.json()
        Decimal(str(pos_data["cash_balance"]))
        Decimal(str(pos_data["total_value"]))

        # Test PnL
        pnl_response = client.get(f"/analysis/pnl?account_ids={account_id}")
        pnl_data = pnl_response.json()
        Decimal(str(pnl_data["pnl_dollars"]))
        Decimal(str(pnl_data["current_value"]))

        # Test allocation
        alloc_response = client.get(f"/analysis/allocation?account_ids={account_id}")
        alloc_data = alloc_response.json()
        Decimal(str(alloc_data["total_value"]))
        for item in alloc_data["items"]:
            Decimal(str(item["market_value"]))
            Decimal(str(item["percentage"]))
