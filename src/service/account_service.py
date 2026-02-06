from dataclasses import dataclass
from typing import List, Optional
import sqlite3

from src.utils.exceptions import ValidationError, NotFoundError
from src.service.util import _load_config


@dataclass
class AccountCreate:
    name: str


class AccountService:
    def __init__(self, account_db_path: Optional[str] = None):
        if account_db_path:
            self._account_db_path = account_db_path
        else:
            config = _load_config()
            self._account_db_path = config.get("AccountDBPath", "accounts.sqlite")
    
    def _validate_account_create(self, data: AccountCreate) -> None:
        if not data.name:
            raise ValidationError("Account name is required")

        # Check if account name is already taken
        conn = sqlite3.connect(self._account_db_path)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM accounts WHERE name = ?", (data.name,))
        existing = cur.fetchone()
        conn.close()
        if existing:
            raise ValidationError(f"Account name '{data.name}' is already taken")

    def create_account(self, account: AccountCreate):
        self._validate_account_create(account)
        self.save_account(account)
    
    def create_batch_account(self, accounts: List[AccountCreate]):
        for account in accounts:
            self._validate_account_create(account)
            self.save_account(account)
    
    def save_account(self, account: AccountCreate):
        conn = sqlite3.connect(self._account_db_path)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO accounts (
                name
            ) VALUES (?)
            """,
            (account.name,),
        )
        conn.commit()
        conn.close()
    
    def list_accounts(self):
        """Return all accounts as small dicts (e.g. for filter dropdown and add/edit account field)."""
        conn = sqlite3.connect(self._account_db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM accounts ORDER BY name")
        rows = cur.fetchall()
        conn.close()
        return [{"name": row[0]} for row in rows]

    def get_account(self, account_name: str):
        conn = sqlite3.connect(self._account_db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts WHERE name = ?", (account_name,))
        account = cur.fetchone()
        if not account:
            raise NotFoundError("Account", account_name)
        return account
    
    def edit_account(self, old_name: str, new_data: AccountCreate):
        if not old_name:
            raise ValidationError("Old account name is required")
        if not new_data.name:
            raise ValidationError("New account name is required")
        # Only check duplicate if name is changing
        if new_data.name != old_name:
            conn = sqlite3.connect(self._account_db_path)
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM accounts WHERE name = ?", (new_data.name,))
            if cur.fetchone():
                conn.close()
                raise ValidationError(f"Account name '{new_data.name}' is already taken")
            conn.close()
        conn = sqlite3.connect(self._account_db_path)
        cur = conn.cursor()
        cur.execute("UPDATE accounts SET name = ? WHERE name = ?", (new_data.name, old_name))
        if cur.rowcount == 0:
            conn.close()
            raise NotFoundError("Account", old_name)
        conn.commit()
        conn.close()
        return self.get_account(new_data.name)
    
    def delete_account(self, account_name: str):
        conn = sqlite3.connect(self._account_db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM accounts WHERE name = ?", (account_name,))
        conn.commit()
        conn.close()