from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Callable, List, Optional
import sqlite3
import uuid

from src.service.enums import TransactionType
from src.utils.exceptions import ValidationError, NotFoundError
from src.service.util import _load_config


def _normalize_symbol(s: Optional[str]) -> Optional[str]:
    """Normalize symbol for storage: strip and uppercase; empty becomes None."""
    if s is None:
        return None
    t = (s or "").strip().upper()
    return t if t else None

@dataclass
class TransactionCreate:
    account_name: str
    txn_type: TransactionType
    txn_time_est: datetime
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    cash_amount: Optional[Decimal] = None
    fees: Decimal = Decimal("0")
    note: Optional[str] = None
    txn_id: Optional[str] = None  # Auto-generated if omitted
    cash_destination_account: Optional[str] = None  # For SELL: account that receives sale proceeds

@dataclass
class TransactionEdit:
    txn_id: str
    account_name: Optional[str] = None
    txn_type: Optional[TransactionType] = None
    txn_time_est: Optional[datetime] = None
    symbol: Optional[str] = None
    quantity: Optional[Decimal] = None
    price: Optional[Decimal] = None
    cash_amount: Optional[Decimal] = None
    fees: Optional[Decimal] = None
    note: Optional[str] = None
    cash_destination_account: Optional[str] = None


def _is_symbol_valid(quote_data: dict, symbol: str) -> bool:
    """Consider symbol valid if we have current_price or a display_name that differs from raw symbol."""
    price = quote_data.get("current_price")
    if price is not None:
        return True
    name = (quote_data.get("display_name") or "").strip()
    return bool(name and name.upper() != (symbol or "").strip().upper())


class TransactionService:
    def __init__(
        self,
        transaction_db_path: Optional[str] = None,
        account_db_path: Optional[str] = None,
        quote_service: Optional[object] = None,
        get_quantity_held: Optional[Callable[[str, str], Decimal]] = None,
    ):
        if transaction_db_path and account_db_path:
            self._transaction_db_path = transaction_db_path
            self._account_db_path = account_db_path
        else:
            config = _load_config()
            self._transaction_db_path = config.get("TransactionDBPath", "transactions.sqlite") or "transactions.sqlite"
            self._account_db_path = config.get("AccountDBPath", "accounts.sqlite") or "accounts.sqlite"
        self._quote_service = quote_service
        self._get_quantity_held = get_quantity_held

    def _validate_transaction_create(self, data: TransactionCreate) -> None:
        if data.txn_time_est is None:
            raise ValidationError("txn_time_est is required")
        account = self._validate_account(data.account_name)
        if data.cash_destination_account is not None:
            self._validate_account(data.cash_destination_account)
        if data.txn_type in (TransactionType.BUY, TransactionType.SELL):
            if not data.symbol:
                raise ValidationError(f"{data.txn_type.value} requires a valid symbol")
            norm_symbol = _normalize_symbol(data.symbol)
            if self._quote_service and norm_symbol:
                quotes = self._quote_service.get_quotes([norm_symbol])
                q = quotes.get(norm_symbol) or {}
                if not _is_symbol_valid(q, data.symbol):
                    raise ValidationError(f"Invalid or unknown symbol: {norm_symbol}")
            if data.quantity is None or data.quantity <= 0:
                raise ValidationError(f"{data.txn_type.value} requires quantity > 0")
            if data.price is None or data.price < 0:
                raise ValidationError(f"{data.txn_type.value} requires price >= 0")
            if data.fees < 0:
                raise ValidationError("Fees cannot be negative")
            if data.txn_type == TransactionType.SELL and self._get_quantity_held and norm_symbol:
                held = self._get_quantity_held(data.account_name, norm_symbol)
                if held <= 0:
                    raise ValidationError(
                        f"You do not hold {norm_symbol} in account {data.account_name}"
                    )
                if held < data.quantity:
                    raise ValidationError(
                        f"Insufficient shares of {norm_symbol} in account {data.account_name}. "
                        f"You have {held}, tried to sell {data.quantity}"
                    )
        elif data.txn_type in (TransactionType.CASH_DEPOSIT, TransactionType.CASH_WITHDRAW):
            if data.cash_amount is None or data.cash_amount <= 0:
                raise ValidationError(f"{data.txn_type.value} requires cash_amount > 0")
    
    def _validate_account(self, account_name: str):
        conn = sqlite3.connect(self._account_db_path)
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts WHERE name = ?", (account_name,))
        account = cur.fetchone()
        if not account:
            raise NotFoundError("Account", account_name)
        return account

    def create_transaction(self, transaction: TransactionCreate):
        self._validate_transaction_create(transaction)
        self._save_transaction(transaction)
    
    def create_batch_transaction(self, transactions: List[TransactionCreate]):
        for transaction in transactions:
            self._validate_transaction_create(transaction)
            self._save_transaction(transaction) 
    
    def _save_transaction(self, transaction: TransactionCreate):
        txn_id = transaction.txn_id or uuid.uuid4().hex
        symbol = _normalize_symbol(transaction.symbol)
        conn = sqlite3.connect(self._transaction_db_path)
        cur = conn.cursor()
        cash_dest = transaction.cash_destination_account
        if transaction.txn_type == TransactionType.SELL and cash_dest is None:
            cash_dest = transaction.account_name
        cur.execute(
            """
            INSERT INTO transactions (
                txn_id,
                account_name,
                txn_type,
                txn_time_est,
                symbol,
                quantity,
                price,
                cash_amount,
                fees,
                note,
                cash_destination_account
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                txn_id,
                transaction.account_name,
                transaction.txn_type.value,
                transaction.txn_time_est.isoformat(),
                symbol,
                float(transaction.quantity) if transaction.quantity is not None else None,
                float(transaction.price) if transaction.price is not None else None,
                float(transaction.cash_amount) if transaction.cash_amount is not None else None,
                float(transaction.fees or Decimal("0")),
                transaction.note,
                cash_dest,
            ),
        )
        conn.commit()
        conn.close()

    def list_transactions(
        self,
        account_names: Optional[List[str]] = None,
    ) -> List[dict]:
        """Return all transactions. If account_names is set (non-empty list), only from those accounts; otherwise all accounts."""
        conn = sqlite3.connect(self._transaction_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        if account_names:
            placeholders = ",".join("?" * len(account_names))
            cur.execute(
                f"SELECT * FROM transactions WHERE account_name IN ({placeholders}) ORDER BY txn_time_est DESC",
                account_names,
            )
        else:
            cur.execute("SELECT * FROM transactions ORDER BY txn_time_est DESC")
        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_transaction(self, transaction_id: str) -> dict:
        conn = sqlite3.connect(self._transaction_db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM transactions WHERE txn_id = ?", (transaction_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            raise NotFoundError("Transaction", transaction_id)
        return dict(row)

    def _row_to_transaction_create(self, row: dict) -> TransactionCreate:
        """Convert DB row (dict) to TransactionCreate."""
        txn_time = row.get("txn_time_est")
        if not txn_time:
            raise ValidationError("Transaction has no txn_time_est (required)")
        if isinstance(txn_time, str):
            txn_time = datetime.fromisoformat(txn_time)
        txn_type = row.get("txn_type")
        if isinstance(txn_type, str):
            txn_type = TransactionType(txn_type)

        return TransactionCreate(
            txn_id=row["txn_id"],
            account_name=row["account_name"],
            txn_type=txn_type,
            txn_time_est=txn_time,
            symbol=row.get("symbol"),
            quantity=Decimal(str(row["quantity"])) if row.get("quantity") is not None else None,
            price=Decimal(str(row["price"])) if row.get("price") is not None else None,
            cash_amount=Decimal(str(row["cash_amount"])) if row.get("cash_amount") is not None else None,
            fees=Decimal(str(row.get("fees") or 0)),
            note=row.get("note"),
            cash_destination_account=row.get("cash_destination_account"),
        )

    def edit_transaction(self, data: TransactionEdit) -> dict:
        # 1. Fetch the original transaction
        original = self.get_transaction(data.txn_id)
        txn_create = self._row_to_transaction_create(original)

        # 2. Overwrite only with fields set in TransactionEdit
        if data.account_name is not None:
            txn_create.account_name = data.account_name
        if data.txn_type is not None:
            txn_create.txn_type = data.txn_type
        if data.txn_time_est is not None:
            txn_create.txn_time_est = data.txn_time_est
        if data.symbol is not None:
            txn_create.symbol = _normalize_symbol(data.symbol)
        if data.quantity is not None:
            txn_create.quantity = data.quantity
        if data.price is not None:
            txn_create.price = data.price
        if data.cash_amount is not None:
            txn_create.cash_amount = data.cash_amount
        if data.fees is not None:
            txn_create.fees = data.fees
        if data.note is not None:
            txn_create.note = data.note
        if data.cash_destination_account is not None:
            txn_create.cash_destination_account = data.cash_destination_account

        # 3. Delete old, then create (reuses validation + save)
        conn = sqlite3.connect(self._transaction_db_path)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM transactions WHERE txn_id = ?", (data.txn_id,))
            conn.commit()
        finally:
            conn.close()

        self.create_transaction(txn_create)
        return self.get_transaction(data.txn_id)
    
    def delete_transaction(self, transaction_id: str):
        conn = sqlite3.connect(self._transaction_db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE txn_id = ?", (transaction_id,))
        conn.commit()
        conn.close()

    def update_account_name_in_transactions(self, old_name: str, new_name: str) -> None:
        """Update account_name for all transactions when an account is renamed."""
        conn = sqlite3.connect(self._transaction_db_path)
        cur = conn.cursor()
        cur.execute(
            "UPDATE transactions SET account_name = ? WHERE account_name = ?",
            (new_name, old_name),
        )
        conn.commit()
        conn.close()
    
