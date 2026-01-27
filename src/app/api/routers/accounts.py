"""Account management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_ledger_service
from app.api.schemas import AccountCreate, AccountResponse, AccountListResponse
from app.services import LedgerService
from app.core.exceptions import ValidationError, NotFoundError

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    data: AccountCreate,
    ledger: LedgerService = Depends(get_ledger_service),
) -> AccountResponse:
    """Create a new investment account."""
    try:
        account = ledger.create_account(
            name=data.name,
            cost_basis_method=data.cost_basis_method.value,
        )
        return AccountResponse(
            account_id=account.account_id,
            name=account.name,
            cost_basis_method=account.cost_basis_method,
            created_at_est=account.created_at_est,
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/", response_model=AccountListResponse)
def list_accounts(
    ledger: LedgerService = Depends(get_ledger_service),
) -> AccountListResponse:
    """List all accounts."""
    accounts = ledger.list_accounts()
    return AccountListResponse(
        accounts=[
            AccountResponse(
                account_id=a.account_id,
                name=a.name,
                cost_basis_method=a.cost_basis_method,
                created_at_est=a.created_at_est,
            )
            for a in accounts
        ],
        count=len(accounts),
    )


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: str,
    ledger: LedgerService = Depends(get_ledger_service),
) -> AccountResponse:
    """Get a single account by ID."""
    try:
        account = ledger.get_account(account_id)
        return AccountResponse(
            account_id=account.account_id,
            name=account.name,
            cost_basis_method=account.cost_basis_method,
            created_at_est=account.created_at_est,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
