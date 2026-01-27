"""CSV export functionality."""

import csv
from pathlib import Path
from typing import Optional

from app.services.ledger_service import LedgerService
from app.csv.importer import CSV_COLUMNS


class CsvExporter:
    """
    CSV exporter for transaction data.

    Exports ledger transactions to CSV format for backup/transfer.
    """

    def __init__(self, ledger_service: LedgerService):
        self._ledger = ledger_service

    def export_csv(
        self,
        path: str,
        account_ids: Optional[list[str]] = None,
    ) -> None:
        """
        Export transactions to a CSV file.

        Args:
            path: Output file path
            account_ids: Optional list of accounts to export (None = all)
        """
        # Build account name lookup
        accounts = self._ledger.list_accounts()
        account_names = {acc.account_id: acc.name for acc in accounts}

        # Get transactions
        transactions = self._ledger.query_transactions(
            account_ids=account_ids,
            include_deleted=False,
        )

        # Write CSV
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
            writer.writeheader()

            for txn in transactions:
                writer.writerow({
                    "account_name": account_names.get(txn.account_id, txn.account_id),
                    "txn_time_est": txn.txn_time_est.isoformat() if txn.txn_time_est else "",
                    "type": txn.txn_type.value,
                    "symbol": txn.symbol or "",
                    "quantity": str(txn.quantity) if txn.quantity else "",
                    "price": str(txn.price) if txn.price else "",
                    "cash_amount": str(txn.cash_amount) if txn.cash_amount else "",
                    "fees": str(txn.fees) if txn.fees else "0",
                    "note": txn.note or "",
                })
