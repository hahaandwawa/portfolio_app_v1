"""
Tests for the CSV import / export / template helpers in
``src.service.csv_transaction``.
"""

from datetime import datetime
from decimal import Decimal

import pytest

from src.service.csv_transaction import (
    parse_csv,
    transactions_to_csv,
    generate_template_csv,
    CSV_COLUMNS,
    MAX_IMPORT_ROWS,
)
from src.service.enums import TransactionType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_csv(*rows: str) -> bytes:
    """Stitch header + data rows into UTF-8 bytes."""
    header = ",".join(CSV_COLUMNS)
    lines = [header, *rows]
    return "\n".join(lines).encode("utf-8")


_VALID_BUY_ROW = "MyBroker,BUY,2025-01-15T10:30:00,AAPL,10,185.50,,4.95,Buy Apple"
_VALID_SELL_ROW = "MyBroker,SELL,2025-02-20T14:00:00,TSLA,5,220.00,,4.95,Sell Tesla"
_VALID_DEPOSIT_ROW = "Savings,CASH_DEPOSIT,2025-03-01T09:00:00,,,,5000.00,0,Monthly deposit"
_VALID_WITHDRAW_ROW = "Savings,CASH_WITHDRAW,2025-03-15T11:00:00,,,,1000.00,0,Withdrawal"


# ===================================================================
# parse_csv – happy paths
# ===================================================================


class TestParseCsvHappy:

    def test_single_buy_row(self):
        raw = _make_csv(_VALID_BUY_ROW)
        txns, errors = parse_csv(raw)
        assert errors == []
        assert len(txns) == 1
        t = txns[0]
        assert t.account_name == "MyBroker"
        assert t.txn_type == TransactionType.BUY
        assert t.txn_time_est == datetime(2025, 1, 15, 10, 30, 0)
        assert t.symbol == "AAPL"
        assert t.quantity == Decimal("10")
        assert t.price == Decimal("185.50")
        assert t.cash_amount is None
        assert t.fees == Decimal("4.95")
        assert t.note == "Buy Apple"

    def test_multiple_rows(self):
        raw = _make_csv(_VALID_BUY_ROW, _VALID_SELL_ROW, _VALID_DEPOSIT_ROW, _VALID_WITHDRAW_ROW)
        txns, errors = parse_csv(raw)
        assert errors == []
        assert len(txns) == 4

    def test_case_insensitive_txn_type(self):
        row = "MyBroker,buy,2025-01-15T10:30:00,AAPL,10,185.50,,4.95,Buy Apple"
        txns, errors = parse_csv(_make_csv(row))
        assert errors == []
        assert txns[0].txn_type == TransactionType.BUY

    def test_date_only_format(self):
        row = "MyBroker,BUY,2025-01-15,AAPL,10,185.50,,4.95,"
        txns, errors = parse_csv(_make_csv(row))
        assert errors == []
        assert txns[0].txn_time_est == datetime(2025, 1, 15, 0, 0, 0)

    def test_date_space_time_format(self):
        row = "MyBroker,BUY,2025-01-15 10:30:00,AAPL,10,185.50,,4.95,"
        txns, errors = parse_csv(_make_csv(row))
        assert errors == []
        assert txns[0].txn_time_est == datetime(2025, 1, 15, 10, 30, 0)

    def test_date_iso_with_timezone(self):
        """ISO datetime with +00:00 (or Z) is accepted and converted to naive local."""
        row = "MyBroker,BUY,2026-02-06T21:27:00+00:00,AAPL,10,185.50,,0,"
        txns, errors = parse_csv(_make_csv(row))
        assert errors == []
        assert len(txns) == 1
        assert txns[0].txn_time_est.tzinfo is None
        assert txns[0].txn_time_est.year == 2026 and txns[0].txn_time_est.month == 2 and txns[0].txn_time_est.day == 6

    def test_symbol_uppercased(self):
        row = "MyBroker,BUY,2025-01-15T10:30:00,aapl,10,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert errors == []
        assert txns[0].symbol == "AAPL"

    def test_fees_default_zero(self):
        row = "MyBroker,BUY,2025-01-15T10:30:00,AAPL,10,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert errors == []
        assert txns[0].fees == Decimal("0")

    def test_bom_stripped(self):
        raw = b"\xef\xbb\xbf" + _make_csv(_VALID_BUY_ROW)
        txns, errors = parse_csv(raw)
        assert errors == []
        assert len(txns) == 1

    def test_cash_deposit(self):
        txns, errors = parse_csv(_make_csv(_VALID_DEPOSIT_ROW))
        assert errors == []
        t = txns[0]
        assert t.txn_type == TransactionType.CASH_DEPOSIT
        assert t.cash_amount == Decimal("5000.00")
        assert t.symbol is None
        assert t.quantity is None
        assert t.price is None

    def test_txn_id_generated(self):
        txns, _ = parse_csv(_make_csv(_VALID_BUY_ROW))
        assert txns[0].txn_id is not None
        assert len(txns[0].txn_id) == 32  # uuid4 hex


# ===================================================================
# parse_csv – error / validation paths
# ===================================================================


class TestParseCsvErrors:

    def test_empty_file(self):
        txns, errors = parse_csv(b"")
        assert txns == []
        assert len(errors) == 1
        assert "empty" in errors[0].lower() or "header" in errors[0].lower()

    def test_missing_required_column(self):
        bad_header = "account_name,txn_type\nMyBroker,BUY"
        txns, errors = parse_csv(bad_header.encode("utf-8"))
        assert txns == []
        assert any("txn_time_est" in e for e in errors)

    def test_invalid_txn_type(self):
        row = "MyBroker,INVALID,2025-01-15T10:30:00,AAPL,10,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert len(errors) == 1
        assert "txn_type" in errors[0].lower()

    def test_missing_account_name(self):
        row = ",BUY,2025-01-15T10:30:00,AAPL,10,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert len(errors) == 1
        assert "account_name" in errors[0].lower()

    def test_missing_txn_time(self):
        row = "MyBroker,BUY,,AAPL,10,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert len(errors) == 1

    def test_invalid_date(self):
        row = "MyBroker,BUY,not-a-date,AAPL,10,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert len(errors) == 1
        assert "date" in errors[0].lower()

    def test_buy_missing_symbol(self):
        row = "MyBroker,BUY,2025-01-15T10:30:00,,10,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert any("symbol" in e.lower() for e in errors)

    def test_buy_missing_quantity(self):
        row = "MyBroker,BUY,2025-01-15T10:30:00,AAPL,,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert any("quantity" in e.lower() for e in errors)

    def test_buy_zero_quantity(self):
        row = "MyBroker,BUY,2025-01-15T10:30:00,AAPL,0,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert any("quantity" in e.lower() for e in errors)

    def test_buy_negative_price(self):
        row = "MyBroker,BUY,2025-01-15T10:30:00,AAPL,10,-5,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert any("price" in e.lower() for e in errors)

    def test_cash_deposit_missing_cash_amount(self):
        row = "Savings,CASH_DEPOSIT,2025-03-01T09:00:00,,,,,,deposit"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert any("cash_amount" in e.lower() for e in errors)

    def test_negative_fees(self):
        row = "MyBroker,BUY,2025-01-15T10:30:00,AAPL,10,185.50,,-5,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert any("fees" in e.lower() for e in errors)

    def test_invalid_number_in_quantity(self):
        row = "MyBroker,BUY,2025-01-15T10:30:00,AAPL,abc,185.50,,,"
        txns, errors = parse_csv(_make_csv(row))
        assert len(txns) == 0
        assert any("quantity" in e.lower() for e in errors)

    def test_best_effort_partial_import(self):
        """Valid rows are kept; bad rows produce errors."""
        good = _VALID_BUY_ROW
        bad = "MyBroker,INVALID,2025-01-15T10:30:00,AAPL,10,185.50,,,"
        txns, errors = parse_csv(_make_csv(good, bad))
        assert len(txns) == 1
        assert len(errors) == 1

    def test_not_utf8(self):
        raw = b"\xff\xfe" + b"\x00" * 10
        txns, errors = parse_csv(raw)
        assert txns == []
        assert any("utf-8" in e.lower() for e in errors)


# ===================================================================
# transactions_to_csv
# ===================================================================


class TestTransactionsToCsv:

    def test_empty_list(self):
        csv_text = transactions_to_csv([])
        lines = csv_text.strip().splitlines()
        assert len(lines) == 1  # header only
        assert lines[0] == ",".join(CSV_COLUMNS)

    def test_single_buy_row(self):
        row = {
            "account_name": "MyBroker",
            "txn_type": "BUY",
            "txn_time_est": "2025-01-15T10:30:00",
            "symbol": "AAPL",
            "quantity": 10.0,
            "price": 185.5,
            "cash_amount": None,
            "fees": 4.95,
            "note": "Buy Apple",
        }
        csv_text = transactions_to_csv([row])
        lines = csv_text.strip().splitlines()
        assert len(lines) == 2
        assert "MyBroker" in lines[1]
        assert "AAPL" in lines[1]

    def test_cash_deposit_row(self):
        row = {
            "account_name": "Savings",
            "txn_type": "CASH_DEPOSIT",
            "txn_time_est": "2025-03-01T09:00:00",
            "symbol": None,
            "quantity": None,
            "price": None,
            "cash_amount": 5000.0,
            "fees": 0,
            "note": "Monthly deposit",
        }
        csv_text = transactions_to_csv([row])
        lines = csv_text.strip().splitlines()
        assert len(lines) == 2
        assert "5000" in lines[1]

    def test_multiple_rows(self):
        rows = [
            {
                "account_name": "A",
                "txn_type": "BUY",
                "txn_time_est": "2025-01-01",
                "symbol": "AAPL",
                "quantity": 1,
                "price": 100,
                "cash_amount": None,
                "fees": 0,
                "note": "",
            },
            {
                "account_name": "B",
                "txn_type": "CASH_DEPOSIT",
                "txn_time_est": "2025-02-01",
                "symbol": None,
                "quantity": None,
                "price": None,
                "cash_amount": 500,
                "fees": 0,
                "note": "",
            },
        ]
        csv_text = transactions_to_csv(rows)
        lines = csv_text.strip().splitlines()
        assert len(lines) == 3  # header + 2


# ===================================================================
# generate_template_csv
# ===================================================================


class TestGenerateTemplateCsv:

    def test_has_header(self):
        csv_text = generate_template_csv()
        lines = csv_text.strip().splitlines()
        assert lines[0] == ",".join(CSV_COLUMNS)

    def test_has_example_rows(self):
        csv_text = generate_template_csv()
        lines = csv_text.strip().splitlines()
        # header + 4 example rows (BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAW)
        assert len(lines) >= 5

    def test_contains_all_txn_types(self):
        csv_text = generate_template_csv()
        for tt in TransactionType:
            assert tt.value in csv_text


# ===================================================================
# Round-trip: parse → export → re-parse
# ===================================================================


class TestRoundTrip:

    def test_export_then_import(self):
        """Rows exported as CSV can be re-imported losslessly."""
        db_rows = [
            {
                "account_name": "Broker1",
                "txn_type": "BUY",
                "txn_time_est": "2025-06-01T09:30:00",
                "symbol": "MSFT",
                "quantity": 20.0,
                "price": 310.25,
                "cash_amount": None,
                "fees": 1.0,
                "note": "round trip",
            },
            {
                "account_name": "Broker2",
                "txn_type": "CASH_DEPOSIT",
                "txn_time_est": "2025-06-02T12:00:00",
                "symbol": None,
                "quantity": None,
                "price": None,
                "cash_amount": 2500.0,
                "fees": 0,
                "note": "",
            },
        ]
        csv_text = transactions_to_csv(db_rows)
        txns, errors = parse_csv(csv_text.encode("utf-8"))
        assert errors == []
        assert len(txns) == 2
        assert txns[0].symbol == "MSFT"
        assert txns[0].quantity == Decimal("20.0")
        assert txns[1].txn_type == TransactionType.CASH_DEPOSIT
        assert txns[1].cash_amount == Decimal("2500.0")
