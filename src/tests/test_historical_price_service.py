"""
Tests for HistoricalPriceService: SQLite cache, forward-fill, get_price_on_date.
Mock yfinance to avoid network.
"""

from datetime import date, datetime, timedelta

import pytest

from src.service.historical_price_service import HistoricalPriceService


@pytest.fixture
def historical_price_service(historical_prices_db_path):
    return HistoricalPriceService(db_path=historical_prices_db_path)


def test_get_historical_prices_empty_symbols(historical_price_service):
    out = historical_price_service.get_historical_prices(
        [], date(2024, 1, 1), date(2024, 1, 5)
    )
    assert out == {}


def test_get_historical_prices_invalid_date_range(historical_price_service):
    out = historical_price_service.get_historical_prices(
        ["AAPL"], date(2024, 1, 10), date(2024, 1, 5)
    )
    assert out == {"AAPL": []}


def test_get_historical_prices_forward_fill_and_last_trading_date(
    historical_price_service, monkeypatch
):
    """Mock yfinance to return one trading day; assert calendar days and last_trading_date."""
    import pandas as pd

    def mock_download(*args, **kwargs):
        # Return DataFrame with one row: 2024-01-03 (Wednesday) close 150.0
        idx = pd.DatetimeIndex([pd.Timestamp("2024-01-03")])
        return pd.DataFrame({"Close": [150.0]}, index=idx)

    monkeypatch.setattr(
        "src.service.historical_price_service._get_yf",
        lambda: type("yf", (), {"download": mock_download})(),
    )
    out = historical_price_service.get_historical_prices(
        ["AAPL"],
        date(2024, 1, 1),
        date(2024, 1, 5),
    )
    assert "AAPL" in out
    series = out["AAPL"]
    assert len(series) == 5  # Jan 1–5
    # Jan 1, 2: no data yet -> close None, last_trading_date still the date
    assert series[0]["date"] == "2024-01-01"
    assert series[0]["close"] is None
    assert series[0]["last_trading_date"] == "2024-01-01"
    assert series[1]["date"] == "2024-01-02"
    assert series[1]["close"] is None
    # Jan 3: trading day
    assert series[2]["date"] == "2024-01-03"
    assert series[2]["close"] == 150.0
    assert series[2]["last_trading_date"] == "2024-01-03"
    # Jan 4, 5: forward-filled
    assert series[3]["close"] == 150.0
    assert series[3]["last_trading_date"] == "2024-01-03"
    assert series[4]["close"] == 150.0
    assert series[4]["last_trading_date"] == "2024-01-03"


def test_get_historical_prices_persists_to_db(
    historical_price_service, historical_prices_db_path, monkeypatch
):
    """After fetch, data is in SQLite; second call (no refresh) can use cache."""
    import pandas as pd
    import sqlite3

    call_count = [0]

    def mock_download(*args, **kwargs):
        call_count[0] += 1
        idx = pd.DatetimeIndex([pd.Timestamp("2024-06-01")])
        return pd.DataFrame({"Close": [200.0]}, index=idx)

    monkeypatch.setattr(
        "src.service.historical_price_service._get_yf",
        lambda: type("yf", (), {"download": mock_download})(),
    )
    historical_price_service.get_historical_prices(
        ["MSFT"], date(2024, 6, 1), date(2024, 6, 3)
    )
    assert call_count[0] == 1
    conn = sqlite3.connect(historical_prices_db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT symbol, date, close_price FROM historical_prices WHERE symbol = 'MSFT'"
    )
    rows = cur.fetchall()
    conn.close()
    assert len(rows) >= 1
    assert any(r[1] == "2024-06-01" and r[2] == 200.0 for r in rows)


def test_get_price_on_date(historical_price_service, monkeypatch):
    """get_price_on_date returns close for that date (or forward-filled)."""
    import pandas as pd

    def mock_download(*args, **kwargs):
        idx = pd.DatetimeIndex([pd.Timestamp("2024-02-15")])
        return pd.DataFrame({"Close": [175.5]}, index=idx)

    monkeypatch.setattr(
        "src.service.historical_price_service._get_yf",
        lambda: type("yf", (), {"download": mock_download})(),
    )
    price = historical_price_service.get_price_on_date("AAPL", date(2024, 2, 15))
    assert price == 175.5

    price_sunday = historical_price_service.get_price_on_date("AAPL", date(2024, 2, 18))
    assert price_sunday == 175.5  # forward-filled from 2024-02-15


def test_get_price_on_date_empty_symbol_returns_none(historical_price_service):
    assert historical_price_service.get_price_on_date("", date(2024, 1, 1)) is None
    assert historical_price_service.get_price_on_date("  ", date(2024, 1, 1)) is None


def test_price_type_close_stored(historical_price_service, historical_prices_db_path, monkeypatch):
    """V1 stores price_type = 'close'."""
    import pandas as pd
    import sqlite3

    def mock_download(*args, **kwargs):
        idx = pd.DatetimeIndex([pd.Timestamp("2024-03-01")])
        return pd.DataFrame({"Close": [100.0]}, index=idx)

    monkeypatch.setattr(
        "src.service.historical_price_service._get_yf",
        lambda: type("yf", (), {"download": mock_download})(),
    )
    historical_price_service.get_historical_prices(
        ["GOOG"], date(2024, 3, 1), date(2024, 3, 1)
    )
    conn = sqlite3.connect(historical_prices_db_path)
    cur = conn.cursor()
    cur.execute("SELECT price_type FROM historical_prices WHERE symbol = 'GOOG' LIMIT 1")
    row = cur.fetchone()
    conn.close()
    assert row is not None
    assert row[0] == "close"
