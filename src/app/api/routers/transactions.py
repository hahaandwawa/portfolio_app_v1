import math
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, UploadFile, File
from fastapi.responses import Response

from src.service.transaction_service import TransactionService, TransactionCreate, TransactionEdit
from src.service.account_service import AccountService, AccountCreate
from src.service.enums import TransactionType
from src.service.csv_transaction import parse_csv, transactions_to_csv, generate_template_csv
from src.utils.exceptions import ValidationError, NotFoundError
from src.app.api.schemas.transaction import (
    TransactionCreate as TransactionCreateSchema,
    TransactionEdit as TransactionEditSchema,
    TransactionOut,
    TransactionListResponse,
    TransactionImportResult,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _get_transaction_service() -> TransactionService:
    return TransactionService()


def _get_account_service() -> AccountService:
    return AccountService()


def _row_to_out(row: dict) -> TransactionOut:
    qty = row.get("quantity")
    price = row.get("price")
    cash = row.get("cash_amount")
    amount = None
    if qty is not None and price is not None:
        amount = round(float(qty) * float(price), 2)
    elif cash is not None:
        amount = round(float(cash), 2)

    return TransactionOut(
        txn_id=row["txn_id"],
        account_name=row["account_name"],
        txn_type=row["txn_type"],
        txn_time_est=row["txn_time_est"],
        symbol=row.get("symbol"),
        quantity=float(qty) if qty is not None else None,
        price=float(price) if price is not None else None,
        cash_amount=float(cash) if cash is not None else None,
        amount=amount,
        fees=float(row.get("fees") or 0),
        note=row.get("note"),
    )


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    account: Optional[list[str]] = Query(None, alias="account"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    """
    List transactions with optional account filter and pagination.
    account: list of account names to filter (empty = all)
    """
    svc = _get_transaction_service()
    account_names = account if account else None
    rows = svc.list_transactions(account_names=account_names)
    total = len(rows)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    end = start + page_size
    page_rows = rows[start:end]
    items = [_row_to_out(r) for r in page_rows]
    return TransactionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ---------------------------------------------------------------------------
# CSV Import / Export / Template
# ---------------------------------------------------------------------------


@router.post("/import", response_model=TransactionImportResult, status_code=201)
def import_transactions(file: UploadFile = File(...)):
    """Bulk-import transactions from a CSV file.

    Missing accounts referenced by ``account_name`` are auto-created.
    Returns a summary with imported count, newly-created account names,
    and any per-row errors (best-effort: valid rows are imported even when
    some rows fail).
    """
    # 1. Read and parse CSV ---------------------------------------------------
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    transactions, parse_errors = parse_csv(raw)

    if not transactions and parse_errors:
        # Nothing could be parsed – return 400 with the errors
        raise HTTPException(status_code=400, detail=parse_errors[0])

    # 2. Auto-create missing accounts ----------------------------------------
    acct_svc = _get_account_service()
    existing_accounts: set[str] = set()
    for acct in acct_svc.list_accounts():
        existing_accounts.add(acct["name"])

    needed_names = {t.account_name for t in transactions}
    accounts_created: list[str] = []
    for name in sorted(needed_names):
        if name not in existing_accounts:
            try:
                acct_svc.create_account(AccountCreate(name=name))
                accounts_created.append(name)
                existing_accounts.add(name)
            except ValidationError:
                # Account was created between our check and the insert (race)
                pass

    # 3. Batch-create transactions -------------------------------------------
    txn_svc = _get_transaction_service()
    imported_count = 0
    for txn in transactions:
        try:
            txn_svc.create_transaction(txn)
            imported_count += 1
        except (ValidationError, NotFoundError) as exc:
            parse_errors.append(f"account={txn.account_name}: {exc.message}")

    return TransactionImportResult(
        imported=imported_count,
        accounts_created=accounts_created,
        errors=parse_errors,
    )


@router.get("/export")
def export_transactions(
    account: Optional[list[str]] = Query(None, alias="account"),
):
    """Download transactions as a CSV file.

    Supports optional ``account`` query param (repeatable) to filter.
    """
    svc = _get_transaction_service()
    account_names = account if account else None
    rows = svc.list_transactions(account_names=account_names)

    csv_text = transactions_to_csv(rows)

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


@router.get("/template")
def download_template():
    """Download a template CSV with header and example rows."""
    csv_text = generate_template_csv()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="transactions_template.csv"'},
    )


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(data: TransactionCreateSchema):
    """Create a new transaction."""
    svc = _get_transaction_service()
    try:
        txn_type = TransactionType(data.txn_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid txn_type: {data.txn_type}")

    txn_time = data.txn_time_est
    if isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00"))

    txn_id = uuid.uuid4().hex
    create = TransactionCreate(
        txn_id=txn_id,
        account_name=data.account_name,
        txn_type=txn_type,
        txn_time_est=txn_time,
        symbol=data.symbol,
        quantity=Decimal(str(data.quantity)) if data.quantity is not None else None,
        price=Decimal(str(data.price)) if data.price is not None else None,
        cash_amount=Decimal(str(data.cash_amount)) if data.cash_amount is not None else None,
        fees=Decimal(str(data.fees)),
        note=data.note,
    )
    try:
        svc.create_transaction(create)
        row = svc.get_transaction(txn_id)
        return _row_to_out(row)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.put("/{txn_id}", response_model=TransactionOut)
def update_transaction(txn_id: str, data: TransactionEditSchema):
    """Update an existing transaction."""
    svc = _get_transaction_service()
    txn_time = data.txn_time_est
    if txn_time is not None and isinstance(txn_time, str):
        txn_time = datetime.fromisoformat(txn_time.replace("Z", "+00:00"))

    try:
        txn_type_val = TransactionType(data.txn_type) if data.txn_type else None
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid txn_type: {data.txn_type}")

    edit = TransactionEdit(
        txn_id=txn_id,
        account_name=data.account_name,
        txn_type=txn_type_val,
        txn_time_est=txn_time,
        symbol=data.symbol,
        quantity=Decimal(str(data.quantity)) if data.quantity is not None else None,
        price=Decimal(str(data.price)) if data.price is not None else None,
        cash_amount=Decimal(str(data.cash_amount)) if data.cash_amount is not None else None,
        fees=Decimal(str(data.fees)) if data.fees is not None else None,
        note=data.note,
    )
    try:
        row = svc.edit_transaction(edit)
        return _row_to_out(row)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.delete("/{txn_id}", status_code=204)
def delete_transaction(txn_id: str):
    """Delete a transaction."""
    svc = _get_transaction_service()
    try:
        svc.delete_transaction(txn_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
