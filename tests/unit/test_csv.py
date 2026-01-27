"""
Unit tests for CSV functionality.

Tests cover:
- Template generation
- Import with valid data
- Import error handling
- Export functionality
- Round-trip import/export
"""

import csv
import os
import tempfile
import pytest
from decimal import Decimal
from pathlib import Path

from app.csv import CsvImporter, CsvExporter, CsvTemplateGenerator
from app.csv.importer import CSV_COLUMNS
from app.services import LedgerService, PortfolioEngine
from app.services.ledger_service import TransactionCreate
from app.domain.models import Account, TransactionType
from app.core.exceptions import ValidationError

from tests.conftest import (
    eastern_datetime,
    create_buy_transaction_data,
    create_cash_deposit_data,
)


# =============================================================================
# TEMPLATE GENERATION TESTS
# =============================================================================


class TestCsvTemplateGenerator:
    """Tests for CSV template generation."""

    def test_template_has_required_headers(
        self,
        csv_template_generator: CsvTemplateGenerator,
        temp_csv_file: str,
    ):
        """
        GIVEN CsvTemplateGenerator
        WHEN I generate a template
        THEN the file contains all required headers
        """
        csv_template_generator.generate_template(temp_csv_file)

        with open(temp_csv_file, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)

        assert headers == CSV_COLUMNS

    def test_template_includes_example_rows(
        self,
        csv_template_generator: CsvTemplateGenerator,
        temp_csv_file: str,
    ):
        """
        GIVEN CsvTemplateGenerator
        WHEN I generate a template
        THEN example rows are included
        """
        csv_template_generator.generate_template(temp_csv_file)

        with open(temp_csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) >= 1  # At least one example row

    def test_template_example_has_all_transaction_types(
        self,
        csv_template_generator: CsvTemplateGenerator,
        temp_csv_file: str,
    ):
        """
        GIVEN CsvTemplateGenerator
        WHEN I generate a template
        THEN examples include BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAW
        """
        csv_template_generator.generate_template(temp_csv_file)

        with open(temp_csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            types = {row["type"] for row in reader}

        expected_types = {"BUY", "SELL", "CASH_DEPOSIT", "CASH_WITHDRAW"}
        assert expected_types.issubset(types)

    def test_template_creates_parent_directories(
        self,
        csv_template_generator: CsvTemplateGenerator,
    ):
        """
        GIVEN a path with non-existent parent directories
        WHEN I generate a template
        THEN directories are created
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "nested", "dir", "template.csv")

            csv_template_generator.generate_template(path)

            assert os.path.exists(path)


# =============================================================================
# IMPORT TESTS - VALID DATA
# =============================================================================


class TestCsvImportValid:
    """Tests for CSV import with valid data."""

    def test_import_valid_rows(
        self,
        csv_importer: CsvImporter,
        ledger_service: LedgerService,
        temp_csv_file: str,
        sample_csv_content: str,
    ):
        """
        GIVEN a CSV file with 3 valid transaction rows
        WHEN I import
        THEN summary.imported_count = 3 and transactions exist
        """
        # Write sample content
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(sample_csv_content)

        summary = csv_importer.import_csv(temp_csv_file)

        assert summary.imported_count == 3
        assert summary.error_count == 0

        # Verify transactions exist
        transactions = ledger_service.query_transactions()
        assert len(transactions) == 3

    def test_import_creates_account_if_not_exists(
        self,
        csv_importer: CsvImporter,
        ledger_service: LedgerService,
        temp_csv_file: str,
    ):
        """
        GIVEN a CSV with an account name that doesn't exist
        WHEN I import
        THEN account is created
        """
        content = """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
NewAccount,2024-01-15 10:30:00,CASH_DEPOSIT,,,,10000,0,Initial deposit
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Verify account doesn't exist
        accounts_before = ledger_service.list_accounts()
        assert not any(a.name == "NewAccount" for a in accounts_before)

        csv_importer.import_csv(temp_csv_file)

        # Verify account was created
        accounts_after = ledger_service.list_accounts()
        assert any(a.name == "NewAccount" for a in accounts_after)

    def test_import_reuses_existing_account(
        self,
        csv_importer: CsvImporter,
        ledger_service: LedgerService,
        temp_csv_file: str,
        sample_account: Account,
    ):
        """
        GIVEN a CSV with an existing account name
        WHEN I import
        THEN transactions are added to existing account
        """
        content = f"""account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
{sample_account.name},2024-01-15 10:30:00,CASH_DEPOSIT,,,,10000,0,Deposit
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        csv_importer.import_csv(temp_csv_file)

        # Verify transaction added to existing account
        transactions = ledger_service.query_transactions(
            account_ids=[sample_account.account_id],
        )
        assert len(transactions) == 1
        assert transactions[0].account_id == sample_account.account_id

    def test_import_handles_optional_fields(
        self,
        csv_importer: CsvImporter,
        ledger_service: LedgerService,
        temp_csv_file: str,
    ):
        """
        GIVEN a CSV with some optional fields empty
        WHEN I import
        THEN import succeeds with None for optional fields
        """
        content = """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
TestAccount,2024-01-15 10:30:00,CASH_DEPOSIT,,,,10000,,
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        summary = csv_importer.import_csv(temp_csv_file)

        assert summary.imported_count == 1
        assert summary.error_count == 0

    def test_import_batch_id_is_set(
        self,
        csv_importer: CsvImporter,
        temp_csv_file: str,
        sample_csv_content: str,
    ):
        """
        GIVEN any valid CSV
        WHEN I import
        THEN import_batch_id is set
        """
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(sample_csv_content)

        summary = csv_importer.import_csv(temp_csv_file)

        assert summary.import_batch_id is not None


# =============================================================================
# IMPORT TESTS - ERROR HANDLING
# =============================================================================


class TestCsvImportErrors:
    """Tests for CSV import error handling."""

    def test_import_file_not_found_raises(
        self,
        csv_importer: CsvImporter,
    ):
        """
        GIVEN a non-existent file path
        WHEN I import
        THEN ValidationError is raised
        """
        with pytest.raises(ValidationError) as exc_info:
            csv_importer.import_csv("/nonexistent/path/file.csv")

        assert "File not found" in str(exc_info.value.message)

    def test_import_missing_columns_raises(
        self,
        csv_importer: CsvImporter,
        temp_csv_file: str,
    ):
        """
        GIVEN a CSV missing required columns
        WHEN I import
        THEN ValidationError is raised
        """
        content = """account_name,type
TestAccount,CASH_DEPOSIT
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        with pytest.raises(ValidationError) as exc_info:
            csv_importer.import_csv(temp_csv_file)

        assert "Missing required columns" in str(exc_info.value.message)

    def test_import_invalid_type_captured_in_errors(
        self,
        csv_importer: CsvImporter,
        temp_csv_file: str,
    ):
        """
        GIVEN a CSV with invalid transaction type
        WHEN I import
        THEN error is captured with row number
        """
        content = """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
TestAccount,2024-01-15 10:30:00,INVALID_TYPE,,,,,0,
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        summary = csv_importer.import_csv(temp_csv_file)

        assert summary.error_count == 1
        assert any("INVALID_TYPE" in err for err in summary.errors)
        assert any("Row 2" in err for err in summary.errors)

    def test_import_invalid_decimal_captured_in_errors(
        self,
        csv_importer: CsvImporter,
        temp_csv_file: str,
    ):
        """
        GIVEN a CSV with non-numeric value in numeric field
        WHEN I import
        THEN error is captured
        """
        content = """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
TestAccount,2024-01-15 10:30:00,BUY,AAPL,not_a_number,185.00,,0,
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        summary = csv_importer.import_csv(temp_csv_file)

        assert summary.error_count == 1
        assert any("Invalid decimal" in err for err in summary.errors)

    def test_import_missing_account_name_captured(
        self,
        csv_importer: CsvImporter,
        temp_csv_file: str,
    ):
        """
        GIVEN a CSV with missing account_name
        WHEN I import
        THEN error is captured
        """
        content = """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
,2024-01-15 10:30:00,CASH_DEPOSIT,,,,10000,0,
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        summary = csv_importer.import_csv(temp_csv_file)

        assert summary.error_count == 1
        assert any("account_name" in err.lower() for err in summary.errors)

    def test_import_partial_success(
        self,
        csv_importer: CsvImporter,
        ledger_service: LedgerService,
        temp_csv_file: str,
    ):
        """
        GIVEN a CSV with some valid and some invalid rows
        WHEN I import
        THEN valid rows are imported, invalid are captured
        """
        content = """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
TestAccount,2024-01-15 10:30:00,CASH_DEPOSIT,,,,10000,0,Valid row
TestAccount,2024-01-16 10:30:00,INVALID_TYPE,,,,5000,0,Invalid row
TestAccount,2024-01-17 10:30:00,CASH_DEPOSIT,,,,5000,0,Valid row
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        summary = csv_importer.import_csv(temp_csv_file)

        assert summary.imported_count == 2
        assert summary.error_count == 1

        # Verify 2 transactions were imported
        transactions = ledger_service.query_transactions()
        assert len(transactions) == 2

    def test_import_empty_file(
        self,
        csv_importer: CsvImporter,
        temp_csv_file: str,
    ):
        """
        GIVEN a CSV with only headers (no data rows)
        WHEN I import
        THEN import succeeds with 0 imported
        """
        content = """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        summary = csv_importer.import_csv(temp_csv_file)

        assert summary.imported_count == 0
        assert summary.error_count == 0


# =============================================================================
# EXPORT TESTS
# =============================================================================


class TestCsvExport:
    """Tests for CSV export functionality."""

    def test_export_creates_file_with_headers(
        self,
        csv_exporter: CsvExporter,
        temp_csv_file: str,
    ):
        """
        GIVEN any state
        WHEN I export
        THEN file is created with correct headers
        """
        csv_exporter.export_csv(temp_csv_file)

        with open(temp_csv_file, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)

        assert headers == CSV_COLUMNS

    def test_export_includes_transactions(
        self,
        csv_exporter: CsvExporter,
        ledger_service: LedgerService,
        sample_account: Account,
        temp_csv_file: str,
    ):
        """
        GIVEN account has transactions
        WHEN I export
        THEN transactions are in the file
        """
        # Add transactions
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))

        csv_exporter.export_csv(temp_csv_file)

        with open(temp_csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2

    def test_export_only_non_deleted(
        self,
        csv_exporter: CsvExporter,
        ledger_service: LedgerService,
        sample_account: Account,
        temp_csv_file: str,
    ):
        """
        GIVEN account has 3 transactions, 1 deleted
        WHEN I export
        THEN only 2 transactions are exported
        """
        # Add 3 transactions
        txn1 = ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="MSFT",
            quantity=Decimal("5"),
            price=Decimal("375.00"),
        ))

        # Delete one
        ledger_service.soft_delete_transaction(txn1.txn_id)

        csv_exporter.export_csv(temp_csv_file)

        with open(temp_csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2

    def test_export_filters_by_account_ids(
        self,
        csv_exporter: CsvExporter,
        ledger_service: LedgerService,
        account_factory,
        temp_csv_file: str,
    ):
        """
        GIVEN transactions in multiple accounts
        WHEN I export with specific account_ids
        THEN only those accounts' transactions are exported
        """
        account_a = account_factory(name="Account A")
        account_b = account_factory(name="Account B")

        # Add to both accounts
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=account_a.account_id,
            amount=Decimal("5000"),
        ))
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=account_b.account_id,
            amount=Decimal("3000"),
        ))

        # Export only account_a
        csv_exporter.export_csv(temp_csv_file, account_ids=[account_a.account_id])

        with open(temp_csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["account_name"] == "Account A"

    def test_export_uses_account_name(
        self,
        csv_exporter: CsvExporter,
        ledger_service: LedgerService,
        sample_account: Account,
        temp_csv_file: str,
    ):
        """
        GIVEN transactions exist
        WHEN I export
        THEN account_name column contains account name, not ID
        """
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000"),
        ))

        csv_exporter.export_csv(temp_csv_file)

        with open(temp_csv_file, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert rows[0]["account_name"] == sample_account.name
        assert rows[0]["account_name"] != sample_account.account_id


# =============================================================================
# ROUND-TRIP TESTS
# =============================================================================


class TestCsvRoundTrip:
    """Tests for export then import round-trip."""

    def test_round_trip_preserves_data(
        self,
        csv_importer: CsvImporter,
        csv_exporter: CsvExporter,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
        temp_csv_file: str,
    ):
        """
        GIVEN an account with transactions
        WHEN I export then import into new account
        THEN data is preserved (ignoring IDs)
        """
        # Create original transactions
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000"),
            txn_time_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
            fees=Decimal("4.95"),
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        # Get original data
        original_txns = ledger_service.query_transactions(
            account_ids=[sample_account.account_id],
        )

        # Export
        csv_exporter.export_csv(temp_csv_file, account_ids=[sample_account.account_id])

        # Modify CSV to use new account name
        with open(temp_csv_file, newline="", encoding="utf-8") as f:
            content = f.read().replace(sample_account.name, "ImportedAccount")
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Import
        summary = csv_importer.import_csv(temp_csv_file)
        assert summary.imported_count == 2
        assert summary.error_count == 0

        # Verify imported data
        accounts = ledger_service.list_accounts()
        imported_account = next(a for a in accounts if a.name == "ImportedAccount")

        imported_txns = ledger_service.query_transactions(
            account_ids=[imported_account.account_id],
        )

        assert len(imported_txns) == len(original_txns)

        # Compare by type and key fields
        original_set = {
            (t.txn_type, t.symbol, t.quantity, t.price, t.cash_amount)
            for t in original_txns
        }
        imported_set = {
            (t.txn_type, t.symbol, t.quantity, t.price, t.cash_amount)
            for t in imported_txns
        }

        assert original_set == imported_set

    def test_round_trip_symbol_normalization(
        self,
        csv_importer: CsvImporter,
        ledger_service: LedgerService,
        temp_csv_file: str,
    ):
        """
        GIVEN lowercase symbols in CSV
        WHEN I import
        THEN symbols are normalized to uppercase
        """
        content = """account_name,txn_time_est,type,symbol,quantity,price,cash_amount,fees,note
TestAccount,2024-01-15 14:00:00,BUY,aapl,10,185.00,,0,
"""
        with open(temp_csv_file, "w", encoding="utf-8") as f:
            f.write(content)

        csv_importer.import_csv(temp_csv_file)

        transactions = ledger_service.query_transactions()
        assert transactions[0].symbol == "AAPL"
