"""Net value curve API: GET /net-value-curve."""

from datetime import datetime, date
from typing import Optional

from fastapi import APIRouter, Query

from src.service.transaction_service import TransactionService
from src.service.historical_price_service import HistoricalPriceService
from src.service.net_value_service import NetValueService
from src.app.api.schemas.net_value import NetValueCurveResponse


router = APIRouter(prefix="/net-value-curve", tags=["net-value-curve"])

_net_value_service: Optional[NetValueService] = None


def _get_net_value_service() -> NetValueService:
    global _net_value_service
    if _net_value_service is None:
        from src.service.util import _load_config
        config = _load_config()
        txn_path = config.get("TransactionDBPath", "./data/transactions.sqlite")
        acc_path = config.get("AccountDBPath", "./data/accounts.sqlite")
        prices_path = config.get("HistoricalPricesDBPath", "./data/historical_prices.sqlite")
        txn_svc = TransactionService(
            transaction_db_path=txn_path,
            account_db_path=acc_path,
        )
        price_svc = HistoricalPriceService(db_path=prices_path)
        _net_value_service = NetValueService(
            transaction_service=txn_svc,
            historical_price_service=price_svc,
        )
    return _net_value_service


def _parse_optional_date(s: Optional[str]):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


@router.get("", response_model=NetValueCurveResponse)
def get_net_value_curve(
    account: Optional[list[str]] = Query(None, alias="account"),
    start_date: Optional[str] = Query(None, description="ISO date (default: first transaction date)"),
    end_date: Optional[str] = Query(None, description="ISO date (default: today)"),
    include_cash: bool = Query(True, description="When true, market value = equity (stocks + cash)"),
    refresh: bool = Query(False, description="When true, overwrite cached prices for the requested range"),
):
    """
    Return net value curve: baseline (Holdings Cost) and market value per day.
    Columnar arrays; tooltips use last_trading_date on non-trading days.
    """
    svc = _get_net_value_service()
    account_names = account if account else None
    start_d = _parse_optional_date(start_date)
    end_d = _parse_optional_date(end_date)
    raw = svc.get_net_value_curve(
        account_names=account_names,
        start_date=start_d,
        end_date=end_d,
        include_cash=include_cash,
        refresh_prices=refresh,
    )
    return NetValueCurveResponse(**raw)
