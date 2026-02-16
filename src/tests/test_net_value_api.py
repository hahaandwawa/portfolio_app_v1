"""
Integration tests for GET /net-value-curve API.
Uses TestClient; patches net value service to use test DBs and mock prices.
"""

from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.app.main import app
from src.service.transaction_service import TransactionService
from src.service.historical_price_service import HistoricalPriceService
from src.service.net_value_service import NetValueService
from decimal import Decimal

from src.service.enums import TransactionType
from src.tests.conftest import make_transaction_create


def _date_str(d):
    return d.isoformat()


def _parse_date(s):
    if hasattr(s, "year"):
        return s
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()


@pytest.fixture
def mock_price_svc_for_api(historical_prices_db_path):
    """HistoricalPriceService with test DB that returns fixed prices (no yfinance)."""
    class MockFetch:
        def get_historical_prices(self, symbols, start, end, refresh=False):
            start = _parse_date(start)
            end = _parse_date(end)
            result = {}
            for sym in symbols:
                out = []
                d = start
                while d <= end:
                    date_s = _date_str(d)
                    out.append({"date": date_s, "close": 100.0, "last_trading_date": date_s})
                    d += timedelta(days=1)
                result[sym] = out
            return result
    return MockFetch()


@pytest.fixture
def net_value_service_for_api(
    transaction_service,
    historical_prices_db_path,
    mock_price_svc_for_api,
):
    price_svc = HistoricalPriceService(db_path=historical_prices_db_path)
    # Replace internal fetch with our mock so we don't call yfinance
    price_svc.get_historical_prices = mock_price_svc_for_api.get_historical_prices
    return NetValueService(
        transaction_service=transaction_service,
        historical_price_service=price_svc,
    )


@pytest.fixture
def client_with_net_value(
    net_value_service_for_api,
    transaction_service,
    account_for_transactions,
):
    """Patch the router's _get_net_value_service to return our test service."""
    from src.app.api import routers
    net_value_router = routers.net_value
    original = net_value_router._get_net_value_service
    net_value_router._get_net_value_service = lambda: net_value_service_for_api
    try:
        with TestClient(app) as c:
            yield c
    finally:
        net_value_router._get_net_value_service = original


class TestNetValueCurveAPI:
    def test_get_net_value_curve_empty_returns_200(self, client_with_net_value):
        r = client_with_net_value.get("/net-value-curve")
        assert r.status_code == 200
        data = r.json()
        assert data["dates"] == []
        # Default include_cash=True, so baseline_label should be "Book Value"
        assert data["baseline_label"] == "Book Value (cash + holdings cost)"
        assert data["price_type"] == "close"
        assert data["includes_cash"] is True

    def test_get_net_value_curve_with_account_param(
        self, client_with_net_value, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("1000"),
                txn_time_est=datetime(2024, 5, 1),
                txn_id="dep1",
            )
        )
        r = client_with_net_value.get("/net-value-curve", params={"account": account_for_transactions})
        assert r.status_code == 200
        data = r.json()
        assert len(data["dates"]) >= 1
        assert data["market_value"][-1] == 1000.0
        assert data["includes_cash"] is True

    def test_get_net_value_curve_include_cash_false(
        self, client_with_net_value, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("5"),
                price=Decimal("100"),
                txn_time_est=datetime(2024, 6, 1),
                txn_id="buy1",
            )
        )
        r = client_with_net_value.get(
            "/net-value-curve",
            params={"account": account_for_transactions, "include_cash": "false"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["includes_cash"] is False
        # Market value = positions only (5 * 100 mock = 500), no cash
        assert data["market_value"][-1] == 500.0

    def test_get_net_value_curve_response_has_last_trading_date(
        self, client_with_net_value, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("1"),
                price=Decimal("50"),
                txn_time_est=datetime(2024, 7, 1),
                txn_id="buy2",
            )
        )
        r = client_with_net_value.get(
            "/net-value-curve",
            params={
                "account": account_for_transactions,
                "start_date": "2024-07-01",
                "end_date": "2024-07-05",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "last_trading_date" in data
        assert len(data["last_trading_date"]) == len(data["dates"])
        assert "profit_loss_pct" in data
        # Default include_cash=True, so baseline_label should be "Book Value"
        assert data["baseline_label"] == "Book Value (cash + holdings cost)"
