"""
Unit tests for AnalysisService.

Tests cover:
- Today P/L calculation
- Multi-account P/L aggregation
- Allocation breakdown
- Allocation percentage validation
- Positions with prices
"""

import pytest
from decimal import Decimal
from typing import Callable

from app.services import AnalysisService, PortfolioEngine, LedgerService, MarketDataService
from app.domain.models import Account, TransactionType
from app.domain.views import TodayPnlView, AllocationView

from tests.conftest import (
    DeterministicMarketProvider,
    eastern_datetime,
    create_buy_transaction_data,
    create_cash_deposit_data,
    assert_decimal_equal,
)


# =============================================================================
# TODAY P/L TESTS
# =============================================================================


class TestTodayPnl:
    """Tests for today's P/L calculation."""

    def test_today_pnl_single_position(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has 10 shares of AAPL
        AND quote: AAPL last=$185.50, prev=$184.25
        WHEN I call today_pnl
        THEN pnl_dollars = 10 * (185.50 - 184.25) = $12.50
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),  # Cost basis doesn't affect today's P/L
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        pnl = analysis_service.today_pnl([sample_account.account_id])

        expected_pnl = Decimal("10") * (Decimal("185.50") - Decimal("184.25"))
        assert_decimal_equal(pnl.pnl_dollars, expected_pnl)

    def test_today_pnl_percent_calculation(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has 10 shares of AAPL
        AND quote: AAPL last=$185.50, prev=$184.25
        WHEN I call today_pnl
        THEN pnl_percent = (12.50 / 1842.50) * 100 = 0.68%
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        pnl = analysis_service.today_pnl([sample_account.account_id])

        # prev_close_value = 10 * 184.25 = 1842.50
        # pnl_percent = (12.50 / 1842.50) * 100 = 0.68%
        expected_percent = (Decimal("12.50") / Decimal("1842.50") * 100).quantize(Decimal("0.01"))
        assert pnl.pnl_percent is not None
        assert_decimal_equal(pnl.pnl_percent, expected_percent, tolerance=Decimal("0.1"))

    def test_today_pnl_multiple_positions(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has 10 AAPL and 5 TSLA
        AND quotes: AAPL +$1.25, TSLA -$1.35
        WHEN I call today_pnl
        THEN pnl = (10 * 1.25) + (5 * -1.35) = 12.50 - 6.75 = $5.75
        """
        # AAPL: 10 shares
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        # TSLA: 5 shares (TSLA is down: last=248.75, prev=250.10)
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="TSLA",
            quantity=Decimal("5"),
            price=Decimal("245.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        pnl = analysis_service.today_pnl([sample_account.account_id])

        # AAPL: 10 * (185.50 - 184.25) = 10 * 1.25 = 12.50
        # TSLA: 5 * (248.75 - 250.10) = 5 * (-1.35) = -6.75
        # Total: 12.50 - 6.75 = 5.75
        expected_pnl = Decimal("12.50") + Decimal("-6.75")
        assert_decimal_equal(pnl.pnl_dollars, expected_pnl)

    def test_today_pnl_multi_account_aggregation(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        account_factory: Callable,
    ):
        """
        GIVEN Account A has 10 AAPL, Account B has 5 AAPL
        WHEN I call today_pnl for both accounts
        THEN pnl = 15 * (185.50 - 184.25) = $18.75
        """
        account_a = account_factory(name="Account A")
        account_b = account_factory(name="Account B")

        # Account A: 10 AAPL
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_a.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        portfolio_engine.rebuild_account(account_a.account_id)

        # Account B: 5 AAPL
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_b.account_id,
            symbol="AAPL",
            quantity=Decimal("5"),
            price=Decimal("182.00"),
        ))
        portfolio_engine.rebuild_account(account_b.account_id)

        pnl = analysis_service.today_pnl([account_a.account_id, account_b.account_id])

        # 15 shares * $1.25 = $18.75
        expected_pnl = Decimal("15") * Decimal("1.25")
        assert_decimal_equal(pnl.pnl_dollars, expected_pnl)

    def test_today_pnl_empty_account(
        self,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has no positions
        WHEN I call today_pnl
        THEN pnl_dollars = $0, pnl_percent = None
        """
        portfolio_engine.rebuild_account(sample_account.account_id)

        pnl = analysis_service.today_pnl([sample_account.account_id])

        assert pnl.pnl_dollars == Decimal("0")
        assert pnl.pnl_percent is None

    def test_today_pnl_empty_account_list(
        self,
        analysis_service: AnalysisService,
    ):
        """
        GIVEN empty account list
        WHEN I call today_pnl
        THEN pnl_dollars = $0
        """
        pnl = analysis_service.today_pnl([])

        assert pnl.pnl_dollars == Decimal("0")

    def test_today_pnl_includes_current_value(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has positions
        WHEN I call today_pnl
        THEN current_value and prev_close_value are populated
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        pnl = analysis_service.today_pnl([sample_account.account_id])

        # current_value = 10 * 185.50 = 1855.00
        # prev_close_value = 10 * 184.25 = 1842.50
        assert_decimal_equal(pnl.current_value, Decimal("1855.00"))
        assert_decimal_equal(pnl.prev_close_value, Decimal("1842.50"))


# =============================================================================
# ALLOCATION TESTS
# =============================================================================


class TestAllocation:
    """Tests for allocation breakdown calculation."""

    def test_allocation_single_position(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has only AAPL
        WHEN I call allocation
        THEN AAPL is 100%
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        allocation = analysis_service.allocation([sample_account.account_id])

        assert len(allocation.items) == 1
        assert allocation.items[0].symbol == "AAPL"
        assert_decimal_equal(allocation.items[0].percentage, Decimal("100.00"))

    def test_allocation_multiple_positions(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has 10 AAPL and 5 MSFT
        WHEN I call allocation
        THEN each has appropriate percentage based on market value
        """
        # AAPL: 10 shares @ $185.50 = $1,855.00
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        # MSFT: 5 shares @ $378.25 = $1,891.25
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="MSFT",
            quantity=Decimal("5"),
            price=Decimal("370.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        allocation = analysis_service.allocation([sample_account.account_id])

        assert len(allocation.items) == 2

        # Total: 1855.00 + 1891.25 = 3746.25
        # AAPL: 1855.00 / 3746.25 = 49.52%
        # MSFT: 1891.25 / 3746.25 = 50.48%
        items_dict = {item.symbol: item for item in allocation.items}

        assert_decimal_equal(
            items_dict["AAPL"].market_value,
            Decimal("1855.00"),
        )
        assert_decimal_equal(
            items_dict["MSFT"].market_value,
            Decimal("1891.25"),
        )

    def test_allocation_percentages_sum_to_100(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has multiple positions
        WHEN I call allocation
        THEN all percentages sum to 100% (within tolerance)
        """
        # Add multiple positions
        for symbol, qty in [("AAPL", 10), ("MSFT", 5), ("GOOGL", 8)]:
            ledger_service.add_transaction(create_buy_transaction_data(
                account_id=sample_account.account_id,
                symbol=symbol,
                quantity=Decimal(str(qty)),
                price=Decimal("100.00"),
            ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        allocation = analysis_service.allocation([sample_account.account_id])

        total_percentage = sum(item.percentage for item in allocation.items)
        assert_decimal_equal(total_percentage, Decimal("100.00"), tolerance=Decimal("0.1"))

    def test_allocation_sorted_by_market_value_descending(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN multiple positions with different values
        WHEN I call allocation
        THEN items are sorted by market value descending
        """
        # Add positions with different values
        # AAPL: 10 * 185.50 = 1855
        # MSFT: 5 * 378.25 = 1891.25 (highest)
        # GOOGL: 3 * 142.75 = 428.25 (lowest)
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="MSFT",
            quantity=Decimal("5"),
            price=Decimal("370.00"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="GOOGL",
            quantity=Decimal("3"),
            price=Decimal("140.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        allocation = analysis_service.allocation([sample_account.account_id])

        # Should be sorted: MSFT, AAPL, GOOGL
        assert allocation.items[0].symbol == "MSFT"
        assert allocation.items[1].symbol == "AAPL"
        assert allocation.items[2].symbol == "GOOGL"

    def test_allocation_total_value(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN multiple positions
        WHEN I call allocation
        THEN total_value equals sum of market values
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="MSFT",
            quantity=Decimal("5"),
            price=Decimal("370.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        allocation = analysis_service.allocation([sample_account.account_id])

        # 1855.00 + 1891.25 = 3746.25
        expected_total = Decimal("1855.00") + Decimal("1891.25")
        assert_decimal_equal(allocation.total_value, expected_total)

    def test_allocation_empty_account(
        self,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has no positions
        WHEN I call allocation
        THEN items is empty and total_value is 0
        """
        portfolio_engine.rebuild_account(sample_account.account_id)

        allocation = analysis_service.allocation([sample_account.account_id])

        assert allocation.items == []
        assert allocation.total_value == Decimal("0")

    def test_allocation_empty_account_list(
        self,
        analysis_service: AnalysisService,
    ):
        """
        GIVEN empty account list
        WHEN I call allocation
        THEN returns empty allocation
        """
        allocation = analysis_service.allocation([])

        assert allocation.items == []


# =============================================================================
# POSITIONS WITH PRICES TESTS
# =============================================================================


class TestPositionsWithPrices:
    """Tests for getting positions enriched with market prices."""

    def test_positions_with_prices_includes_last_price(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has AAPL position
        WHEN I call get_positions_with_prices
        THEN result includes last_price from market data
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = analysis_service.get_positions_with_prices([sample_account.account_id])

        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].shares == Decimal("10")
        assert positions[0].last_price == Decimal("185.50")

    def test_positions_with_prices_includes_market_value(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has AAPL position
        WHEN I call get_positions_with_prices
        THEN market_value = shares * last_price
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = analysis_service.get_positions_with_prices([sample_account.account_id])

        expected_value = Decimal("10") * Decimal("185.50")
        assert_decimal_equal(positions[0].market_value, expected_value)

    def test_positions_with_prices_includes_prev_close(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has AAPL position
        WHEN I call get_positions_with_prices
        THEN prev_close is included
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = analysis_service.get_positions_with_prices([sample_account.account_id])

        assert positions[0].prev_close == Decimal("184.25")

    def test_positions_with_prices_empty_account(
        self,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has no positions
        WHEN I call get_positions_with_prices
        THEN empty list is returned
        """
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = analysis_service.get_positions_with_prices([sample_account.account_id])

        assert positions == []

    def test_positions_with_prices_aggregates_accounts(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        account_factory: Callable,
    ):
        """
        GIVEN Account A has 10 AAPL, Account B has 5 AAPL
        WHEN I call get_positions_with_prices for both
        THEN aggregated position shows 15 AAPL
        """
        account_a = account_factory(name="Account A")
        account_b = account_factory(name="Account B")

        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_a.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_b.account_id,
            symbol="AAPL",
            quantity=Decimal("5"),
            price=Decimal("182.00"),
        ))

        portfolio_engine.rebuild_account(account_a.account_id)
        portfolio_engine.rebuild_account(account_b.account_id)

        positions = analysis_service.get_positions_with_prices([
            account_a.account_id,
            account_b.account_id,
        ])

        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].shares == Decimal("15")


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestAnalysisEdgeCases:
    """Tests for edge cases in analysis calculations."""

    def test_pnl_with_unknown_symbol(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has position in symbol not known to market provider
        WHEN I call today_pnl
        THEN unknown symbol is excluded from P/L (graceful handling)
        """
        # Add a symbol that's known
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("180.00"),
        ))
        # Add a symbol that's NOT in deterministic provider
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="UNKNOWN",
            quantity=Decimal("100"),
            price=Decimal("50.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        pnl = analysis_service.today_pnl([sample_account.account_id])

        # Only AAPL contributes: 10 * 1.25 = $12.50
        # UNKNOWN is excluded because no quote
        assert_decimal_equal(pnl.pnl_dollars, Decimal("12.50"))

    def test_allocation_with_fractional_shares(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        analysis_service: AnalysisService,
        sample_account: Account,
    ):
        """
        GIVEN account has fractional shares
        WHEN I call allocation
        THEN market values are calculated correctly
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("0.5"),
            price=Decimal("180.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        allocation = analysis_service.allocation([sample_account.account_id])

        # 0.5 * 185.50 = 92.75
        expected_value = Decimal("0.5") * Decimal("185.50")
        assert_decimal_equal(allocation.items[0].market_value, expected_value)
