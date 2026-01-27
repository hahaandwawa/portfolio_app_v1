"""Analysis service for portfolio analytics."""

from decimal import Decimal
from typing import Optional

from app.core.timezone import now_eastern
from app.domain.views import (
    PositionView,
    Quote,
    TodayPnlView,
    AllocationItem,
    AllocationView,
)
from app.services.portfolio_engine import PortfolioEngine
from app.services.market_data_service import MarketDataService


class AnalysisService:
    """
    Service for portfolio analytics and reporting.

    Computes today's P/L, allocation breakdown, and other metrics.
    """

    def __init__(
        self,
        portfolio_engine: PortfolioEngine,
        market_data_service: MarketDataService,
    ):
        self._portfolio = portfolio_engine
        self._market = market_data_service

    def today_pnl(self, account_ids: list[str]) -> TodayPnlView:
        """
        Calculate today's P/L for given accounts.

        Formula: Σ(shares × (last_price - prev_close))
        Returns $ amount and % change vs previous close.
        """
        if not account_ids:
            return TodayPnlView(
                pnl_dollars=Decimal("0"),
                pnl_percent=None,
                as_of=now_eastern(),
            )

        # Get aggregated positions
        positions = self._portfolio.aggregate_positions(account_ids)
        if not positions:
            return TodayPnlView(
                pnl_dollars=Decimal("0"),
                pnl_percent=None,
                as_of=now_eastern(),
            )

        # Fetch quotes
        symbols = [p.symbol for p in positions]
        quotes = self._market.get_quotes(symbols)

        # Calculate P/L
        total_pnl = Decimal("0")
        prev_close_value = Decimal("0")
        current_value = Decimal("0")
        as_of = now_eastern()

        for position in positions:
            quote = quotes.get(position.symbol)
            if quote:
                position_pnl = position.shares * (quote.last_price - quote.prev_close)
                total_pnl += position_pnl
                prev_close_value += position.shares * quote.prev_close
                current_value += position.shares * quote.last_price
                as_of = quote.as_of  # Use quote timestamp

        # Calculate percentage
        pnl_percent: Optional[Decimal] = None
        if prev_close_value != Decimal("0"):
            pnl_percent = (total_pnl / prev_close_value * 100).quantize(Decimal("0.01"))

        return TodayPnlView(
            pnl_dollars=total_pnl.quantize(Decimal("0.01")),
            pnl_percent=pnl_percent,
            prev_close_value=prev_close_value.quantize(Decimal("0.01")),
            current_value=current_value.quantize(Decimal("0.01")),
            as_of=as_of,
        )

    def allocation(self, account_ids: list[str]) -> AllocationView:
        """
        Calculate portfolio allocation breakdown.

        Returns market value and percentage for each holding.
        """
        if not account_ids:
            return AllocationView(as_of=now_eastern())

        # Get aggregated positions
        positions = self._portfolio.aggregate_positions(account_ids)
        if not positions:
            return AllocationView(as_of=now_eastern())

        # Fetch quotes
        symbols = [p.symbol for p in positions]
        quotes = self._market.get_quotes(symbols)

        # Calculate allocations
        items: list[AllocationItem] = []
        total_value = Decimal("0")
        as_of = now_eastern()

        for position in positions:
            quote = quotes.get(position.symbol)
            if quote:
                market_value = (position.shares * quote.last_price).quantize(Decimal("0.01"))
                total_value += market_value
                items.append(
                    AllocationItem(
                        symbol=position.symbol,
                        market_value=market_value,
                        percentage=Decimal("0"),  # Will be calculated below
                    )
                )
                as_of = quote.as_of

        # Calculate percentages
        if total_value != Decimal("0"):
            for item in items:
                item.percentage = (item.market_value / total_value * 100).quantize(
                    Decimal("0.01")
                )

        # Sort by market value descending
        items.sort(key=lambda x: x.market_value, reverse=True)

        return AllocationView(
            items=items,
            total_value=total_value.quantize(Decimal("0.01")),
            as_of=as_of,
        )

    def get_positions_with_prices(
        self,
        account_ids: list[str],
    ) -> list[PositionView]:
        """
        Get positions enriched with current market prices.

        Returns positions with last_price and market_value populated.
        """
        positions = self._portfolio.aggregate_positions(account_ids)
        if not positions:
            return []

        symbols = [p.symbol for p in positions]
        quotes = self._market.get_quotes(symbols)

        result: list[PositionView] = []
        for position in positions:
            quote = quotes.get(position.symbol)
            if quote:
                market_value = (position.shares * quote.last_price).quantize(Decimal("0.01"))
                result.append(
                    PositionView(
                        symbol=position.symbol,
                        shares=position.shares,
                        last_price=quote.last_price,
                        market_value=market_value,
                        prev_close=quote.prev_close,
                    )
                )
            else:
                result.append(position)

        return result
