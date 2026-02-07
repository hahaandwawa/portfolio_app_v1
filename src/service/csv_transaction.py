"""
CSV Import / Export helpers for transactions.

Responsibilities:
  - Parse a CSV file (bytes or text) into a list of service-layer TransactionCreate objects.
  - Serialize a list of transaction DB rows (dicts) to CSV text.
  - Generate a template CSV (header + example rows).

Dependencies: stdlib `csv`, `io`, `uuid` only.
"""

import csv
import io
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

from src.service.enums import TransactionType
from src.service.transaction_service import TransactionCreate


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CSV_COLUMNS: List[str] = [
    "account_name",
    "txn_type",
    "txn_time_est",
    "symbol",
    "quantity",
    "price",
    "cash_amount",
    "fees",
    "note",
    "cash_destination_account",
]

_REQUIRED_COLUMNS = {"account_name", "txn_type", "txn_time_est"}

_VALID_TXN_TYPES = {t.value for t in TransactionType}

MAX_IMPORT_ROWS = 10_000

# Example rows used in the downloadable template CSV
_TEMPLATE_EXAMPLES: List[dict] = [
    {
        "account_name": "My Brokerage",
        "txn_type": "BUY",
        "txn_time_est": "2025-01-15T10:30:00",
        "symbol": "AAPL",
        "quantity": "10",
        "price": "185.50",
        "cash_amount": "",
        "fees": "4.95",
        "note": "Buy Apple shares",
    },
    {
        "account_name": "My Brokerage",
        "txn_type": "SELL",
        "txn_time_est": "2025-02-20T14:00:00",
        "symbol": "TSLA",
        "quantity": "5",
        "price": "220.00",
        "cash_amount": "",
        "fees": "4.95",
        "note": "Sell Tesla shares",
        "cash_destination_account": "",
    },
    {
        "account_name": "Savings",
        "txn_type": "CASH_DEPOSIT",
        "txn_time_est": "2025-03-01T09:00:00",
        "symbol": "",
        "quantity": "",
        "price": "",
        "cash_amount": "5000.00",
        "fees": "0",
        "note": "Monthly deposit",
    },
    {
        "account_name": "Savings",
        "txn_type": "CASH_WITHDRAW",
        "txn_time_est": "2025-03-15T11:00:00",
        "symbol": "",
        "quantity": "",
        "price": "",
        "cash_amount": "1000.00",
        "fees": "0",
        "note": "Withdrawal",
    },
]


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _strip_bom(text: str) -> str:
    """Remove UTF-8 BOM if present."""
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def _parse_datetime(value: str) -> datetime:
    """Parse ISO-style datetime (with or without timezone), or date-only ``YYYY-MM-DD``.

    Accepts e.g. ``2026-02-06T21:27:00+00:00``, ``2026-02-06T21:27:00``, ``2026-02-06 21:27:00``, ``2026-02-06``.
    Timezone-aware values are converted to naive local time.
    """
    value = value.strip()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        pass
    else:
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date format: '{value}'")


def _to_decimal(value: str, field: str) -> Optional[Decimal]:
    """Convert string to Decimal; empty/whitespace → None."""
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        raise ValueError(f"Invalid number for '{field}': '{value}'")


# ---------------------------------------------------------------------------
# Public API – parse
# ---------------------------------------------------------------------------


def parse_csv(raw: bytes) -> Tuple[List[TransactionCreate], List[str]]:
    """Parse raw CSV bytes into ``TransactionCreate`` objects.

    Returns ``(transactions, errors)`` where *errors* is a list of
    human-readable error strings (one per bad row).  Rows that pass
    validation are included in *transactions*; rows that fail are
    skipped and their error is appended to *errors*.
    """
    try:
        text = raw.decode("utf-8-sig")  # handles BOM automatically
    except UnicodeDecodeError:
        return [], ["File is not valid UTF-8."]

    text = _strip_bom(text)

    reader = csv.DictReader(io.StringIO(text))

    # --- header validation ---------------------------------------------------
    if reader.fieldnames is None:
        return [], ["CSV file is empty or has no header row."]

    # Normalize header names (strip whitespace, lowercase for comparison)
    normalized_headers = {h.strip().lower() for h in reader.fieldnames}
    missing = _REQUIRED_COLUMNS - normalized_headers
    if missing:
        return [], [f"Missing required column(s): {', '.join(sorted(missing))}"]

    # Build a mapping from normalized → original so we can access rows
    header_map = {h.strip().lower(): h for h in reader.fieldnames}

    transactions: List[TransactionCreate] = []
    errors: List[str] = []

    for row_num, raw_row in enumerate(reader, start=2):  # row 1 is header
        if row_num - 1 > MAX_IMPORT_ROWS:
            errors.append(f"Exceeded maximum of {MAX_IMPORT_ROWS} rows. Extra rows ignored.")
            break

        try:
            txn = _parse_row(raw_row, header_map, row_num)
            transactions.append(txn)
        except ValueError as exc:
            errors.append(f"Row {row_num}: {exc}")

    return transactions, errors


def _get_field(raw_row: dict, header_map: dict, field: str) -> str:
    """Get a field value from a CSV row, handling header normalization."""
    key = header_map.get(field.lower())
    if key is None:
        return ""
    value = raw_row.get(key, "")
    return value.strip() if value else ""


def _parse_row(raw_row: dict, header_map: dict, row_num: int) -> TransactionCreate:
    """Parse and validate one CSV row into a ``TransactionCreate``."""
    account_name = _get_field(raw_row, header_map, "account_name")
    if not account_name:
        raise ValueError("account_name is required")

    txn_type_raw = _get_field(raw_row, header_map, "txn_type").upper()
    if txn_type_raw not in _VALID_TXN_TYPES:
        raise ValueError(f"Invalid txn_type '{txn_type_raw}'. Must be one of: {', '.join(sorted(_VALID_TXN_TYPES))}")
    txn_type = TransactionType(txn_type_raw)

    txn_time_str = _get_field(raw_row, header_map, "txn_time_est")
    if not txn_time_str:
        raise ValueError("txn_time_est is required")
    txn_time = _parse_datetime(txn_time_str)

    symbol_raw = _get_field(raw_row, header_map, "symbol").upper() or None
    quantity = _to_decimal(_get_field(raw_row, header_map, "quantity"), "quantity")
    price = _to_decimal(_get_field(raw_row, header_map, "price"), "price")
    cash_amount = _to_decimal(_get_field(raw_row, header_map, "cash_amount"), "cash_amount")
    fees = _to_decimal(_get_field(raw_row, header_map, "fees"), "fees")
    if fees is None:
        fees = Decimal("0")
    note = _get_field(raw_row, header_map, "note") or None
    cash_destination_account = _get_field(raw_row, header_map, "cash_destination_account") or None

    # Type-specific validation
    if txn_type in (TransactionType.BUY, TransactionType.SELL):
        if not symbol_raw:
            raise ValueError(f"{txn_type.value} requires a symbol")
        if quantity is None or quantity <= 0:
            raise ValueError(f"{txn_type.value} requires quantity > 0")
        if price is None or price < 0:
            raise ValueError(f"{txn_type.value} requires price >= 0")
    elif txn_type in (TransactionType.CASH_DEPOSIT, TransactionType.CASH_WITHDRAW):
        if cash_amount is None or cash_amount <= 0:
            raise ValueError(f"{txn_type.value} requires cash_amount > 0")

    if fees < 0:
        raise ValueError("fees must be >= 0")

    return TransactionCreate(
        txn_id=uuid.uuid4().hex,
        account_name=account_name,
        txn_type=txn_type,
        txn_time_est=txn_time,
        symbol=symbol_raw,
        quantity=quantity,
        price=price,
        cash_amount=cash_amount,
        fees=fees,
        note=note,
        cash_destination_account=cash_destination_account,
    )


# ---------------------------------------------------------------------------
# Public API – serialize / export
# ---------------------------------------------------------------------------


def transactions_to_csv(rows: List[dict]) -> str:
    """Serialize a list of transaction DB row dicts to a CSV string.

    Column order follows ``CSV_COLUMNS``.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({
            "account_name": row.get("account_name", ""),
            "txn_type": row.get("txn_type", ""),
            "txn_time_est": row.get("txn_time_est", ""),
            "symbol": row.get("symbol") or "",
            "quantity": row.get("quantity") if row.get("quantity") is not None else "",
            "price": row.get("price") if row.get("price") is not None else "",
            "cash_amount": row.get("cash_amount") if row.get("cash_amount") is not None else "",
            "fees": row.get("fees") if row.get("fees") is not None else "0",
            "note": row.get("note") or "",
            "cash_destination_account": row.get("cash_destination_account") or "",
        })
    return output.getvalue()


# ---------------------------------------------------------------------------
# Public API – template
# ---------------------------------------------------------------------------


def generate_template_csv() -> str:
    """Return a CSV string with the header and example rows for each txn_type."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for example in _TEMPLATE_EXAMPLES:
        writer.writerow(example)
    return output.getvalue()
