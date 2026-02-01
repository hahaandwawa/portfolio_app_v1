"""Database initialization - ensures schema exists."""
from pathlib import Path
import sqlite3

from src.service.util import _load_config


def _create_accounts_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            name TEXT NOT NULL PRIMARY KEY
        )
        """
    )
    conn.commit()


def _create_transactions_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            txn_id TEXT NOT NULL PRIMARY KEY,
            account_name TEXT NOT NULL,
            txn_type TEXT NOT NULL,
            txn_time_est TEXT NOT NULL,
            symbol TEXT,
            quantity REAL,
            price REAL,
            cash_amount REAL,
            fees REAL,
            note TEXT
        )
        """
    )
    conn.commit()


def init_database() -> None:
    """Create data directory and schema if they don't exist."""
    config = _load_config()
    account_path = config.get("AccountDBPath", "./data/accounts.sqlite")
    txn_path = config.get("TransactionDBPath", "./data/transactions.sqlite")

    for path_str in (account_path, txn_path):
        path = Path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)

    conn_acc = sqlite3.connect(account_path)
    _create_accounts_schema(conn_acc)
    conn_acc.close()

    conn_txn = sqlite3.connect(txn_path)
    _create_transactions_schema(conn_txn)
    conn_txn.close()
