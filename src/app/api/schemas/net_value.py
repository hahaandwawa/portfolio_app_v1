"""Pydantic schemas for net value curve API."""

from typing import Optional

from pydantic import BaseModel


class NetValueCurveResponse(BaseModel):
    """Columnar net value curve: baseline (Holdings Cost) and market value over time."""

    baseline_label: str = "Holdings Cost (avg)"
    price_type: str = "close"
    includes_cash: bool = True

    dates: list[str]
    baseline: list[float]
    market_value: list[float]
    profit_loss: list[float]
    profit_loss_pct: list[Optional[float]]
    is_trading_day: list[bool]
    last_trading_date: list[str]
