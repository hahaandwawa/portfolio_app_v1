from fastapi import APIRouter, HTTPException

from src.service.account_service import AccountService, AccountCreate
from src.service.transaction_service import TransactionService
from src.utils.exceptions import ValidationError, NotFoundError
from src.app.api.schemas.account import AccountCreate as AccountCreateSchema, AccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _get_account_service() -> AccountService:
    return AccountService()


def _get_transaction_service() -> TransactionService:
    return TransactionService()


@router.get("", response_model=list[AccountOut])
def list_accounts():
    """List all accounts with transaction counts."""
    svc = _get_account_service()
    raw = svc.list_accounts()
    txn_svc = _get_transaction_service()
    result = []
    for acc in raw:
        count = len(txn_svc.list_transactions(account_names=[acc["name"]]))
        result.append(AccountOut(name=acc["name"], transaction_count=count))
    return result


@router.post("", response_model=AccountOut, status_code=201)
def create_account(data: AccountCreateSchema):
    """Create a new account."""
    svc = _get_account_service()
    try:
        svc.create_account(AccountCreate(name=data.name))
        return AccountOut(name=data.name, transaction_count=0)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.put("/{account_name}", response_model=AccountOut)
def update_account(account_name: str, data: AccountCreateSchema):
    """Update an account's name. Also updates all related transactions."""
    svc = _get_account_service()
    txn_svc = _get_transaction_service()
    try:
        svc.edit_account(account_name, AccountCreate(name=data.name))
        if data.name != account_name:
            txn_svc.update_account_name_in_transactions(account_name, data.name)
        count = len(txn_svc.list_transactions(account_names=[data.name]))
        return AccountOut(name=data.name, transaction_count=count)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.delete("/{account_name}", status_code=204)
def delete_account(account_name: str):
    """Delete an account. Fails if account has transactions."""
    svc = _get_account_service()
    txn_svc = _get_transaction_service()
    count = len(txn_svc.list_transactions(account_names=[account_name]))
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete account with {count} transaction(s). Remove transactions first.",
        )
    try:
        svc.delete_account(account_name)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
