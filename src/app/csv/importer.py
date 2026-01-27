"""CSV import functionality."""

import csv
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from app.core.timezone import parse_datetime_eastern
from app.core.exceptions import ValidationError
from app.domain.models import TransactionType
from app.domain.views import ImportSummary
from app.services.ledger_service import LedgerService, TransactionCreate
from app.services.portfolio_engine import PortfolioEngine


# Expected CSV columns
CSV_COLUMNS = [
    "account_name",
    "txn_time_est",
    "type",
    "symbol",
    "quantity",
    "price",
    "cash_amount",
    "fees",
    "note",
]


class CsvImporter:
    """
    CSV importer for bulk transaction loading.

    Expected format: account_name, txn_time_est, type, symbol, quantity, price, cash_amount, fees, note
    Assumes US/Eastern timezone if not specified.
    """

    def __init__(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
    ):
        self._ledger = ledger_service
        self._portfolio = portfolio_engine

    def import_csv(self, path: str) -> ImportSummary:
        """
        Import transactions from a CSV file.

        Returns summary with imported/skipped/error counts.
        Triggers portfolio rebuild for affected accounts after import.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise ValidationError(f"File not found: {path}")

        summary = ImportSummary(import_batch_id=str(uuid.uuid4()))
        affected_accounts: set[str] = set()
        account_cache: dict[str, str] = {}  # name -> account_id

        with open(file_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            # Validate columns
            if reader.fieldnames:
                missing = set(CSV_COLUMNS) - set(reader.fieldnames)
                if missing:
                    raise ValidationError(f"Missing required columns: {missing}")

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    self._import_row(row, account_cache, affected_accounts)
                    summary.imported_count += 1
                except Exception as e:
                    summary.error_count += 1
                    summary.errors.append(f"Row {row_num}: {str(e)}")

        # Rebuild caches for affected accounts
        for account_id in affected_accounts:
            self._portfolio.rebuild_account(account_id)

        return summary

    def _import_row(
        self,
        row: dict[str, str],
        account_cache: dict[str, str],
        affected_accounts: set[str],
    ) -> None:
        """Import a single row from CSV."""
        account_name = row.get("account_name", "").strip()
        if not account_name:
            raise ValidationError("Missing account_name")

        # Get or create account
        if account_name not in account_cache:
            accounts = self._ledger.list_accounts()
            for acc in accounts:
                if acc.name == account_name:
                    account_cache[account_name] = acc.account_id
                    break
            else:
                # Create new account
                new_account = self._ledger.create_account(account_name)
                account_cache[account_name] = new_account.account_id

        account_id = account_cache[account_name]
        affected_accounts.add(account_id)

        # Parse transaction type
        txn_type_str = row.get("type", "").strip().upper()
        try:
            txn_type = TransactionType(txn_type_str)
        except ValueError:
            raise ValidationError(f"Invalid transaction type: {txn_type_str}")

        # Parse datetime
        txn_time_str = row.get("txn_time_est", "").strip()
        txn_time = parse_datetime_eastern(txn_time_str) if txn_time_str else None

        # Parse numeric fields
        symbol = row.get("symbol", "").strip().upper() or None
        quantity = self._parse_decimal(row.get("quantity", ""))
        price = self._parse_decimal(row.get("price", ""))
        cash_amount = self._parse_decimal(row.get("cash_amount", ""))
        fees = self._parse_decimal(row.get("fees", "")) or Decimal("0")
        note = row.get("note", "").strip() or None

        # Create transaction
        data = TransactionCreate(
            account_id=account_id,
            txn_type=txn_type,
            txn_time_est=txn_time,
            symbol=symbol,
            quantity=quantity,
            price=price,
            cash_amount=cash_amount,
            fees=fees,
            note=note,
        )
        self._ledger.add_transaction(data)

    @staticmethod
    def _parse_decimal(value: str) -> Optional[Decimal]:
        """Parse a decimal value from string, returning None for empty strings."""
        value = value.strip() if value else ""
        if not value:
            return None
        try:
            return Decimal(value)
        except InvalidOperation:
            raise ValidationError(f"Invalid decimal value: {value}")
