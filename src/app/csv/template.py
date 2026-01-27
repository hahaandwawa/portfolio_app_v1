"""CSV template generation."""

import csv
from pathlib import Path

from app.csv.importer import CSV_COLUMNS


class CsvTemplateGenerator:
    """Generator for blank CSV import templates."""

    def generate_template(self, path: str) -> None:
        """
        Generate a blank CSV template with headers and example rows.

        Args:
            path: Output file path for the template
        """
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS)
            writer.writeheader()

            # Write example rows
            example_rows = [
                {
                    "account_name": "Brokerage",
                    "txn_time_est": "2024-01-15 10:30:00",
                    "type": "CASH_DEPOSIT",
                    "symbol": "",
                    "quantity": "",
                    "price": "",
                    "cash_amount": "10000.00",
                    "fees": "0",
                    "note": "Initial deposit",
                },
                {
                    "account_name": "Brokerage",
                    "txn_time_est": "2024-01-15 14:00:00",
                    "type": "BUY",
                    "symbol": "AAPL",
                    "quantity": "10",
                    "price": "185.50",
                    "cash_amount": "",
                    "fees": "0",
                    "note": "Initial AAPL position",
                },
                {
                    "account_name": "Brokerage",
                    "txn_time_est": "2024-02-01 11:00:00",
                    "type": "SELL",
                    "symbol": "AAPL",
                    "quantity": "5",
                    "price": "190.00",
                    "cash_amount": "",
                    "fees": "4.95",
                    "note": "Partial sale",
                },
                {
                    "account_name": "Brokerage",
                    "txn_time_est": "2024-02-15 09:00:00",
                    "type": "CASH_WITHDRAW",
                    "symbol": "",
                    "quantity": "",
                    "price": "",
                    "cash_amount": "500.00",
                    "fees": "0",
                    "note": "Withdrawal",
                },
            ]

            for row in example_rows:
                writer.writerow(row)
