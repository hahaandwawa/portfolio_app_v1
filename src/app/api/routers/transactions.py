"""Transaction management endpoints."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import tempfile
import os

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import FileResponse

from app.api.deps import (
    get_ledger_service,
    get_portfolio_engine,
    get_csv_importer,
    get_csv_exporter,
    get_csv_template_generator,
)
from app.api.schemas import (
    TransactionCreateRequest,
    TransactionUpdateRequest,
    TransactionResponse,
    TransactionListResponse,
    ImportSummaryResponse,
)
from app.services import LedgerService, TransactionCreate, TransactionUpdate, PortfolioEngine
from app.csv import CsvImporter, CsvExporter, CsvTemplateGenerator
from app.domain.models import TransactionType
from app.core.exceptions import ValidationError, NotFoundError

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("/", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def add_transaction(
    data: TransactionCreateRequest,
    ledger: LedgerService = Depends(get_ledger_service),
    portfolio: PortfolioEngine = Depends(get_portfolio_engine),
) -> TransactionResponse:
    """Add a new transaction to the ledger."""
    try:
        txn_create = TransactionCreate(
            account_id=data.account_id,
            txn_type=data.txn_type,
            txn_time_est=data.txn_time_est,
            symbol=data.symbol,
            quantity=data.quantity,
            price=data.price,
            cash_amount=data.cash_amount,
            fees=data.fees,
            note=data.note,
        )
        transaction = ledger.add_transaction(txn_create)

        # Rebuild portfolio cache
        portfolio.rebuild_account(data.account_id)

        return _to_response(transaction)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.get("/", response_model=TransactionListResponse)
def query_transactions(
    account_ids: Optional[str] = Query(None, description="Comma-separated account IDs"),
    symbols: Optional[str] = Query(None, description="Comma-separated symbols"),
    txn_types: Optional[str] = Query(None, description="Comma-separated types"),
    start_date: Optional[datetime] = Query(None, description="Start date filter"),
    end_date: Optional[datetime] = Query(None, description="End date filter"),
    include_deleted: bool = Query(False, description="Include deleted transactions"),
    ledger: LedgerService = Depends(get_ledger_service),
) -> TransactionListResponse:
    """Query transactions with optional filters."""
    # Parse comma-separated values
    account_id_list = account_ids.split(",") if account_ids else None
    symbol_list = [s.upper() for s in symbols.split(",")] if symbols else None
    type_list = [TransactionType(t.strip()) for t in txn_types.split(",")] if txn_types else None

    transactions = ledger.query_transactions(
        account_ids=account_id_list,
        symbols=symbol_list,
        txn_types=type_list,
        start_date=start_date,
        end_date=end_date,
        include_deleted=include_deleted,
    )

    return TransactionListResponse(
        transactions=[_to_response(t) for t in transactions],
        count=len(transactions),
    )


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def edit_transaction(
    transaction_id: str,
    data: TransactionUpdateRequest,
    ledger: LedgerService = Depends(get_ledger_service),
    portfolio: PortfolioEngine = Depends(get_portfolio_engine),
) -> TransactionResponse:
    """Edit an existing transaction."""
    try:
        patch = TransactionUpdate(
            txn_time_est=data.txn_time_est,
            symbol=data.symbol,
            quantity=data.quantity,
            price=data.price,
            cash_amount=data.cash_amount,
            fees=data.fees,
            note=data.note,
        )
        transaction = ledger.edit_transaction(transaction_id, patch)

        # Rebuild portfolio cache
        portfolio.rebuild_account(transaction.account_id)

        return _to_response(transaction)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: str,
    ledger: LedgerService = Depends(get_ledger_service),
    portfolio: PortfolioEngine = Depends(get_portfolio_engine),
) -> None:
    """Soft delete a transaction."""
    try:
        # Get transaction first to know the account_id
        transactions = ledger.query_transactions(include_deleted=True)
        txn = next((t for t in transactions if t.txn_id == transaction_id), None)
        if not txn:
            raise NotFoundError("Transaction", transaction_id)

        ledger.soft_delete_transaction(transaction_id)

        # Rebuild portfolio cache
        portfolio.rebuild_account(txn.account_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)


@router.post("/undo/{account_id}", status_code=status.HTTP_200_OK)
def undo_last_action(
    account_id: str,
    ledger: LedgerService = Depends(get_ledger_service),
    portfolio: PortfolioEngine = Depends(get_portfolio_engine),
) -> dict[str, str]:
    """Undo the last action on an account."""
    try:
        ledger.undo_last_action(account_id)
        portfolio.rebuild_account(account_id)
        return {"status": "success", "message": "Last action undone"}
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    except NotImplementedError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Undo functionality not yet implemented",
        )


@router.post("/import", response_model=ImportSummaryResponse)
async def import_csv(
    file: UploadFile = File(...),
    importer: CsvImporter = Depends(get_csv_importer),
) -> ImportSummaryResponse:
    """Import transactions from a CSV file."""
    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".csv") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        summary = importer.import_csv(tmp_path)
        return ImportSummaryResponse(
            imported_count=summary.imported_count,
            skipped_count=summary.skipped_count,
            error_count=summary.error_count,
            errors=summary.errors,
            import_batch_id=summary.import_batch_id,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)
    finally:
        os.unlink(tmp_path)


@router.get("/export")
def export_csv(
    account_ids: Optional[str] = Query(None, description="Comma-separated account IDs"),
    exporter: CsvExporter = Depends(get_csv_exporter),
) -> FileResponse:
    """Export transactions to a CSV file."""
    account_id_list = account_ids.split(",") if account_ids else None

    # Create temp file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
        tmp_path = tmp.name

    exporter.export_csv(tmp_path, account_ids=account_id_list)

    return FileResponse(
        path=tmp_path,
        filename="transactions_export.csv",
        media_type="text/csv",
    )


@router.get("/template")
def get_csv_template(
    generator: CsvTemplateGenerator = Depends(get_csv_template_generator),
) -> FileResponse:
    """Download a blank CSV import template."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
        tmp_path = tmp.name

    generator.generate_template(tmp_path)

    return FileResponse(
        path=tmp_path,
        filename="import_template.csv",
        media_type="text/csv",
    )


def _to_response(txn) -> TransactionResponse:
    """Convert domain transaction to response schema."""
    return TransactionResponse(
        txn_id=txn.txn_id,
        account_id=txn.account_id,
        txn_time_est=txn.txn_time_est,
        txn_type=txn.txn_type,
        symbol=txn.symbol,
        quantity=txn.quantity,
        price=txn.price,
        cash_amount=txn.cash_amount,
        fees=txn.fees,
        note=txn.note,
        is_deleted=txn.is_deleted,
        created_at_est=txn.created_at_est,
        updated_at_est=txn.updated_at_est,
    )
