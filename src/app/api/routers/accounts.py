from typing import Optional

from fastapi import APIRouter, HTTPException

from src.service.account_service import AccountService, AccountCreate
from src.service.transaction_service import TransactionService
from src.utils.exceptions import ValidationError, NotFoundError
from src.app.api.schemas.account import AccountCreate as AccountCreateSchema, AccountOut

router = APIRouter(prefix="/accounts", tags=["accounts"])

_acct_svc: Optional[AccountService] = None
_txn_svc: Optional[TransactionService] = None


def _get_account_service() -> AccountService:
    global _acct_svc
    if _acct_svc is None:
        _acct_svc = AccountService()
    return _acct_svc


def _get_transaction_service() -> TransactionService:
    global _txn_svc
    if _txn_svc is None:
        _txn_svc = TransactionService()
    return _txn_svc


@router.get("", response_model=list[AccountOut])
def list_accounts():
    """List all accounts with transaction counts."""
    svc = _get_account_service()
    raw = svc.list_accounts()
    txn_svc = _get_transaction_service()
    counts = txn_svc.count_transactions_by_account()
    return [
        AccountOut(name=acc["name"], transaction_count=counts.get(acc["name"], 0))
        for acc in raw
    ]


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
        count = txn_svc.count_transactions(account_names=[data.name])
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
    count = txn_svc.count_transactions(account_names=[account_name])
    if count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete account with {count} transaction(s). Remove transactions first.",
        )
    try:
        svc.delete_account(account_name)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
