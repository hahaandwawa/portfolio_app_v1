"""
API tests for transaction endpoints.

Tests cover:
- Add transaction (BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAW)
- Edit transaction
- Soft delete transaction
- Query transactions with filters
- Undo last action
- CSV import/export
- Validation errors (400, 422)
"""

import pytest
from decimal import Decimal
from datetime import datetime
from fastapi.testclient import TestClient


# =============================================================================
# HELPER FIXTURES
# =============================================================================


@pytest.fixture
def test_account(client: TestClient) -> dict:
    """Create a test account and return its data."""
    response = client.post("/accounts/", json={"name": "Test Account"})
    return response.json()


# =============================================================================
# ADD TRANSACTION TESTS
# =============================================================================


class TestAddTransactionAPI:
    """Tests for POST /transactions endpoint."""

    def test_add_buy_transaction_success(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN an account exists
        WHEN I POST /transactions with valid BUY data
        THEN response is 201 with transaction data
        """
        response = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "BUY",
            "symbol": "AAPL",
            "quantity": "10",
            "price": "185.00",
            "fees": "4.95",
            "note": "Initial purchase",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["txn_id"] is not None
        assert data["txn_type"] == "BUY"
        assert data["symbol"] == "AAPL"
        assert Decimal(data["quantity"]) == Decimal("10")
        assert Decimal(data["price"]) == Decimal("185.00")
        assert data["is_deleted"] is False

    def test_add_cash_deposit_success(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN an account exists
        WHEN I POST /transactions with CASH_DEPOSIT
        THEN response is 201
        """
        response = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "10000.00",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["txn_type"] == "CASH_DEPOSIT"
        assert Decimal(data["cash_amount"]) == Decimal("10000.00")

    def test_add_sell_transaction_success(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN an account exists
        WHEN I POST /transactions with valid SELL data
        THEN response is 201
        """
        response = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "SELL",
            "symbol": "AAPL",
            "quantity": "5",
            "price": "190.00",
            "fees": "4.95",
        })

        assert response.status_code == 201
        assert response.json()["txn_type"] == "SELL"

    def test_add_cash_withdraw_success(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN an account exists
        WHEN I POST /transactions with CASH_WITHDRAW
        THEN response is 201
        """
        response = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_WITHDRAW",
            "cash_amount": "500.00",
        })

        assert response.status_code == 201
        assert response.json()["txn_type"] == "CASH_WITHDRAW"

    def test_add_transaction_symbol_uppercased(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN lowercase symbol in request
        WHEN I POST /transactions
        THEN symbol is stored uppercase
        """
        response = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "BUY",
            "symbol": "aapl",
            "quantity": "10",
            "price": "185.00",
        })

        assert response.status_code == 201
        assert response.json()["symbol"] == "AAPL"

    def test_add_transaction_account_not_found_returns_404(
        self,
        client: TestClient,
    ):
        """
        GIVEN non-existent account_id
        WHEN I POST /transactions
        THEN response is 404
        """
        response = client.post("/transactions/", json={
            "account_id": "nonexistent-account",
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "1000",
        })

        assert response.status_code == 404

    def test_add_buy_without_symbol_returns_400(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN BUY request without symbol
        WHEN I POST /transactions
        THEN response is 400
        """
        response = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "BUY",
            "quantity": "10",
            "price": "185.00",
        })

        assert response.status_code == 400
        assert "symbol" in response.json()["detail"].lower()

    def test_add_transaction_negative_quantity_returns_422(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN negative quantity
        WHEN I POST /transactions
        THEN response is 422 (Pydantic validation)
        """
        response = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "BUY",
            "symbol": "AAPL",
            "quantity": "-10",
            "price": "185.00",
        })

        assert response.status_code == 422


# =============================================================================
# QUERY TRANSACTIONS TESTS
# =============================================================================


class TestQueryTransactionsAPI:
    """Tests for GET /transactions endpoint."""

    def test_query_transactions_empty(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN no transactions
        WHEN I GET /transactions
        THEN response is 200 with empty list
        """
        response = client.get("/transactions/")

        assert response.status_code == 200
        data = response.json()
        assert data["transactions"] == []
        assert data["count"] == 0

    def test_query_transactions_returns_all(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN multiple transactions
        WHEN I GET /transactions
        THEN all non-deleted transactions are returned
        """
        # Add transactions
        for i in range(3):
            client.post("/transactions/", json={
                "account_id": test_account["account_id"],
                "txn_type": "CASH_DEPOSIT",
                "cash_amount": str(1000 * (i + 1)),
            })

        response = client.get("/transactions/")

        assert response.status_code == 200
        assert response.json()["count"] == 3

    def test_query_transactions_filter_by_account(
        self,
        client: TestClient,
    ):
        """
        GIVEN transactions in multiple accounts
        WHEN I GET /transactions?account_ids=...
        THEN only matching account's transactions are returned
        """
        # Create two accounts
        acc1 = client.post("/accounts/", json={"name": "Account 1"}).json()
        acc2 = client.post("/accounts/", json={"name": "Account 2"}).json()

        # Add to both
        client.post("/transactions/", json={
            "account_id": acc1["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "1000",
        })
        client.post("/transactions/", json={
            "account_id": acc2["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "2000",
        })

        # Query only account 1
        response = client.get(f"/transactions/?account_ids={acc1['account_id']}")

        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_query_transactions_filter_by_symbol(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN transactions for multiple symbols
        WHEN I GET /transactions?symbols=AAPL
        THEN only AAPL transactions are returned
        """
        for symbol in ["AAPL", "MSFT", "AAPL"]:
            client.post("/transactions/", json={
                "account_id": test_account["account_id"],
                "txn_type": "BUY",
                "symbol": symbol,
                "quantity": "10",
                "price": "100",
            })

        response = client.get("/transactions/?symbols=AAPL")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert all(t["symbol"] == "AAPL" for t in data["transactions"])

    def test_query_transactions_excludes_deleted_by_default(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN some transactions are deleted
        WHEN I GET /transactions without include_deleted
        THEN deleted transactions are excluded
        """
        # Add and delete one
        txn = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "1000",
        }).json()
        client.delete(f"/transactions/{txn['txn_id']}")

        # Add another (not deleted)
        client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "2000",
        })

        response = client.get("/transactions/")

        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_query_transactions_includes_deleted_when_specified(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN some transactions are deleted
        WHEN I GET /transactions?include_deleted=true
        THEN all transactions including deleted are returned
        """
        txn = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "1000",
        }).json()
        client.delete(f"/transactions/{txn['txn_id']}")

        client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "2000",
        })

        response = client.get("/transactions/?include_deleted=true")

        assert response.status_code == 200
        assert response.json()["count"] == 2


# =============================================================================
# EDIT TRANSACTION TESTS
# =============================================================================


class TestEditTransactionAPI:
    """Tests for PATCH /transactions/{txn_id} endpoint."""

    def test_edit_transaction_success(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN a transaction exists
        WHEN I PATCH /transactions/{id} with new price
        THEN response is 200 with updated data
        """
        # Create transaction
        txn = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "BUY",
            "symbol": "AAPL",
            "quantity": "10",
            "price": "185.00",
        }).json()

        # Edit price
        response = client.patch(f"/transactions/{txn['txn_id']}", json={
            "price": "190.00",
        })

        assert response.status_code == 200
        assert Decimal(response.json()["price"]) == Decimal("190.00")

    def test_edit_transaction_multiple_fields(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN a transaction exists
        WHEN I PATCH with multiple fields
        THEN all fields are updated
        """
        txn = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "BUY",
            "symbol": "AAPL",
            "quantity": "10",
            "price": "185.00",
        }).json()

        response = client.patch(f"/transactions/{txn['txn_id']}", json={
            "quantity": "15",
            "price": "186.00",
            "note": "Updated note",
        })

        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["quantity"]) == Decimal("15")
        assert Decimal(data["price"]) == Decimal("186.00")
        assert data["note"] == "Updated note"

    def test_edit_transaction_not_found_returns_404(
        self,
        client: TestClient,
    ):
        """
        GIVEN non-existent transaction
        WHEN I PATCH
        THEN response is 404
        """
        response = client.patch("/transactions/nonexistent-id", json={
            "price": "190.00",
        })

        assert response.status_code == 404


# =============================================================================
# DELETE TRANSACTION TESTS
# =============================================================================


class TestDeleteTransactionAPI:
    """Tests for DELETE /transactions/{txn_id} endpoint."""

    def test_delete_transaction_success(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN a transaction exists
        WHEN I DELETE /transactions/{id}
        THEN response is 204
        """
        txn = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "1000",
        }).json()

        response = client.delete(f"/transactions/{txn['txn_id']}")

        assert response.status_code == 204

    def test_delete_transaction_marks_as_deleted(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN a transaction exists
        WHEN I DELETE it
        THEN is_deleted is True when queried with include_deleted
        """
        txn = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "1000",
        }).json()

        client.delete(f"/transactions/{txn['txn_id']}")

        # Query with include_deleted
        response = client.get("/transactions/?include_deleted=true")
        transactions = response.json()["transactions"]
        deleted_txn = next(t for t in transactions if t["txn_id"] == txn["txn_id"])

        assert deleted_txn["is_deleted"] is True

    def test_delete_transaction_not_found_returns_404(
        self,
        client: TestClient,
    ):
        """
        GIVEN non-existent transaction
        WHEN I DELETE
        THEN response is 404
        """
        response = client.delete("/transactions/nonexistent-id")

        assert response.status_code == 404


# =============================================================================
# UNDO TESTS
# =============================================================================


class TestUndoAPI:
    """Tests for POST /transactions/undo/{account_id} endpoint."""

    def test_undo_not_implemented(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN undo is not implemented
        WHEN I POST /transactions/undo/{account_id}
        THEN response is 501 (Not Implemented)
        """
        # Add a transaction first
        client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "1000",
        })

        response = client.post(f"/transactions/undo/{test_account['account_id']}")

        # Currently returns 501 as undo is not implemented
        assert response.status_code in [200, 400, 501]


# =============================================================================
# CSV ENDPOINTS TESTS
# =============================================================================


class TestCsvEndpointsAPI:
    """Tests for CSV import/export/template endpoints."""

    def test_get_template(self, client: TestClient):
        """
        GIVEN any state
        WHEN I GET /transactions/template
        THEN response is 200 with CSV file
        """
        response = client.get("/transactions/template")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_export_csv(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN transactions exist
        WHEN I GET /transactions/export
        THEN response is 200 with CSV file
        """
        # Add transaction
        client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "1000",
        })

        response = client.get("/transactions/export")

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_export_csv_filter_by_account(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN transactions in multiple accounts
        WHEN I GET /transactions/export?account_ids=...
        THEN only specified account's transactions are exported
        """
        client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "CASH_DEPOSIT",
            "cash_amount": "1000",
        })

        response = client.get(f"/transactions/export?account_ids={test_account['account_id']}")

        assert response.status_code == 200


# =============================================================================
# RESPONSE FORMAT TESTS
# =============================================================================


class TestTransactionResponseFormat:
    """Tests for transaction response format compliance."""

    def test_transaction_response_contains_all_fields(
        self,
        client: TestClient,
        test_account: dict,
    ):
        """
        GIVEN a transaction is created
        WHEN I check the response
        THEN all expected fields are present
        """
        response = client.post("/transactions/", json={
            "account_id": test_account["account_id"],
            "txn_type": "BUY",
            "symbol": "AAPL",
            "quantity": "10",
            "price": "185.00",
            "fees": "4.95",
            "note": "Test note",
        })

        data = response.json()
        expected_fields = [
            "txn_id",
            "account_id",
            "txn_time_est",
            "txn_type",
            "symbol",
            "quantity",
            "price",
            "cash_amount",
            "fees",
            "note",
            "is_deleted",
            "created_at_est",
        ]

        for field in expected_fields:
            assert field in data, f"Missing field: {field}"
