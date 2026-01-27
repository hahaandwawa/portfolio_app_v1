"""
API tests for account endpoints.

Tests cover:
- Create account (success + validation errors)
- List accounts
- Get single account
- Error responses (400, 404, 422)
"""

import pytest
from fastapi.testclient import TestClient


# =============================================================================
# CREATE ACCOUNT TESTS
# =============================================================================


class TestCreateAccountAPI:
    """Tests for POST /accounts endpoint."""

    def test_create_account_success(self, client: TestClient):
        """
        GIVEN no accounts exist
        WHEN I POST /accounts with valid data
        THEN response is 201 with account data
        """
        response = client.post("/accounts/", json={
            "name": "Brokerage",
            "cost_basis_method": "FIFO",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Brokerage"
        assert data["cost_basis_method"] == "FIFO"
        assert "account_id" in data
        assert data["account_id"] is not None

    def test_create_account_default_cost_basis(self, client: TestClient):
        """
        GIVEN no accounts exist
        WHEN I POST /accounts without cost_basis_method
        THEN FIFO is used as default
        """
        response = client.post("/accounts/", json={
            "name": "Default Account",
        })

        assert response.status_code == 201
        assert response.json()["cost_basis_method"] == "FIFO"

    def test_create_account_with_average_cost_basis(self, client: TestClient):
        """
        GIVEN no accounts exist
        WHEN I POST /accounts with AVERAGE cost basis
        THEN account is created with AVERAGE
        """
        response = client.post("/accounts/", json={
            "name": "Average Account",
            "cost_basis_method": "AVERAGE",
        })

        assert response.status_code == 201
        assert response.json()["cost_basis_method"] == "AVERAGE"

    def test_create_account_duplicate_name_returns_400(self, client: TestClient):
        """
        GIVEN an account named "Brokerage" exists
        WHEN I POST /accounts with same name
        THEN response is 400
        """
        # Create first
        client.post("/accounts/", json={"name": "Brokerage"})

        # Try duplicate
        response = client.post("/accounts/", json={"name": "Brokerage"})

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_create_account_empty_name_returns_422(self, client: TestClient):
        """
        GIVEN empty name
        WHEN I POST /accounts
        THEN response is 422 (Pydantic validation)
        """
        response = client.post("/accounts/", json={
            "name": "",
        })

        assert response.status_code == 422

    def test_create_account_missing_name_returns_422(self, client: TestClient):
        """
        GIVEN request without name field
        WHEN I POST /accounts
        THEN response is 422
        """
        response = client.post("/accounts/", json={})

        assert response.status_code == 422

    def test_create_account_invalid_cost_basis_returns_422(self, client: TestClient):
        """
        GIVEN invalid cost_basis_method
        WHEN I POST /accounts
        THEN response is 422
        """
        response = client.post("/accounts/", json={
            "name": "Invalid",
            "cost_basis_method": "INVALID",
        })

        assert response.status_code == 422


# =============================================================================
# LIST ACCOUNTS TESTS
# =============================================================================


class TestListAccountsAPI:
    """Tests for GET /accounts endpoint."""

    def test_list_accounts_empty(self, client: TestClient):
        """
        GIVEN no accounts exist
        WHEN I GET /accounts
        THEN response is 200 with empty list
        """
        response = client.get("/accounts/")

        assert response.status_code == 200
        data = response.json()
        assert data["accounts"] == []
        assert data["count"] == 0

    def test_list_accounts_multiple(self, client: TestClient):
        """
        GIVEN multiple accounts exist
        WHEN I GET /accounts
        THEN all accounts are returned
        """
        # Create accounts
        for name in ["Account 1", "Account 2", "Account 3"]:
            client.post("/accounts/", json={"name": name})

        response = client.get("/accounts/")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["accounts"]) == 3

    def test_list_accounts_contains_expected_fields(self, client: TestClient):
        """
        GIVEN an account exists
        WHEN I GET /accounts
        THEN response contains all expected fields
        """
        client.post("/accounts/", json={
            "name": "Test Account",
            "cost_basis_method": "FIFO",
        })

        response = client.get("/accounts/")

        assert response.status_code == 200
        account = response.json()["accounts"][0]
        assert "account_id" in account
        assert "name" in account
        assert "cost_basis_method" in account
        assert "created_at_est" in account


# =============================================================================
# GET SINGLE ACCOUNT TESTS
# =============================================================================


class TestGetAccountAPI:
    """Tests for GET /accounts/{account_id} endpoint."""

    def test_get_account_success(self, client: TestClient):
        """
        GIVEN an account exists
        WHEN I GET /accounts/{id}
        THEN response is 200 with account data
        """
        # Create account
        create_response = client.post("/accounts/", json={"name": "Brokerage"})
        account_id = create_response.json()["account_id"]

        # Get account
        response = client.get(f"/accounts/{account_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["account_id"] == account_id
        assert data["name"] == "Brokerage"

    def test_get_account_not_found_returns_404(self, client: TestClient):
        """
        GIVEN no account with given ID
        WHEN I GET /accounts/{id}
        THEN response is 404
        """
        response = client.get("/accounts/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# =============================================================================
# RESPONSE FORMAT TESTS
# =============================================================================


class TestAccountResponseFormat:
    """Tests for account response format compliance."""

    def test_created_at_is_iso_format(self, client: TestClient):
        """
        GIVEN an account is created
        WHEN I retrieve it
        THEN created_at_est is in ISO format
        """
        create_response = client.post("/accounts/", json={"name": "Brokerage"})
        account_id = create_response.json()["account_id"]

        response = client.get(f"/accounts/{account_id}")
        created_at = response.json()["created_at_est"]

        # Should be ISO format: YYYY-MM-DDTHH:MM:SS...
        assert created_at is not None
        assert "T" in created_at or created_at is None  # ISO format contains T

    def test_account_id_is_uuid_format(self, client: TestClient):
        """
        GIVEN an account is created
        WHEN I check account_id
        THEN it is a valid UUID format
        """
        response = client.post("/accounts/", json={"name": "Brokerage"})
        account_id = response.json()["account_id"]

        # UUID format: 8-4-4-4-12
        assert len(account_id) == 36
        assert account_id.count("-") == 4
