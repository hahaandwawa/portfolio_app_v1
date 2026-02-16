"""
Tests for NetValueService: day-by-day holdings, avg-cost mechanics, baseline, market value.
Mock HistoricalPriceService to return controlled prices.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from datetime import timedelta

from src.service.net_value_service import NetValueService
from src.service.enums import TransactionType
from src.tests.conftest import make_transaction_create


def _date_str(d):
    return d.isoformat()


def _parse_date(s):
    if hasattr(s, "year"):
        return s
    from datetime import datetime
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()


@pytest.fixture
def mock_price_svc():
    """Default: every symbol at 100.0 for any date; all days as trading days."""
    def _get(symbols, start, end, refresh=False):
        start = _parse_date(start)
        end = _parse_date(end)
        result = {}
        for sym in symbols:
            out = []
            d = start
            while d <= end:
                date_s = _date_str(d)
                out.append({"date": date_s, "close": 100.0, "last_trading_date": date_s})
                d += timedelta(days=1)
            result[sym] = out
        return result
    class Svc:
        def get_historical_prices(self, syms, s, e, refresh=False):
            return _get(syms, s, e, refresh)
    return Svc()


@pytest.fixture
def net_value_service(transaction_service, mock_price_svc):
    return NetValueService(
        transaction_service=transaction_service,
        historical_price_service=mock_price_svc,
    )


class TestNetValueCurveEmpty:
    def test_no_transactions_returns_empty_curve(self, net_value_service, account_for_transactions):
        out = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions], include_cash=False
        )
        assert out["dates"] == []
        assert out["baseline"] == []
        assert out["baseline_label"] == "Holdings Cost (avg)"
        assert out["includes_cash"] is False


class TestNetValueCurveAvgCostMechanics:
    """BUY updates avg_cost; SELL leaves avg_cost unchanged; shares==0 resets avg_cost."""

    def test_single_buy_baseline_equals_cost(
        self, net_value_service, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("150"),
                fees=Decimal("5"),
                txn_time_est=datetime(2024, 6, 1, 10, 0, 0),
                txn_id="b1",
            )
        )
        out = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 3),
            include_cash=False,  # Stock-only mode for this test
        )
        assert len(out["dates"]) >= 3
        # Baseline = 10 * 150 + 5 = 1505 (stock cost only, no cash)
        assert out["baseline"][-1] == 1505.0
        # Market value = 10 * 100 (mock price) = 1000 (stock_mv only, no cash)
        assert out["market_value"][-1] == 1000.0

    def test_sell_does_not_change_avg_cost(
        self, net_value_service, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("20"),
                price=Decimal("100"),
                fees=Decimal("0"),
                txn_time_est=datetime(2024, 7, 1),
                txn_id="b2",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.SELL,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("120"),
                fees=Decimal("0"),
                txn_time_est=datetime(2024, 7, 2),
                txn_id="s2",
            )
        )
        out = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 5),
            include_cash=False,  # Stock-only mode for this test
        )
        # After sell: 10 shares left, avg_cost still 100 (unchanged)
        # Baseline = 10 * 100 = 1000 (stock cost only)
        baselines = out["baseline"]
        assert baselines[-1] == 1000.0
        # Market value = 10 * 100 (mock) = 1000 (stock_mv only, no cash)
        assert out["market_value"][-1] == 1000.0

    def test_sell_all_resets_avg_cost(
        self, net_value_service, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="MSFT",
                quantity=Decimal("5"),
                price=Decimal("200"),
                txn_time_est=datetime(2024, 8, 1),
                txn_id="b3",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.SELL,
                symbol="MSFT",
                quantity=Decimal("5"),
                price=Decimal("220"),
                txn_time_est=datetime(2024, 8, 2),
                txn_id="s3",
            )
        )
        out = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 8, 1),
            end_date=date(2024, 8, 5),
            include_cash=False,  # Stock-only mode for this test
        )
        # After sell all: baseline = 0 (no stock cost)
        assert out["baseline"][-1] == 0.0
        assert out["profit_loss_pct"][-1] is None  # baseline 0 -> null P/L %


class TestNetValueCurveCash:
    def test_include_cash_adds_cash_to_both_baseline_and_market_value(
        self, net_value_service, transaction_service, account_for_transactions
    ):
        """include_cash=true must affect BOTH baseline and market_value consistently."""
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("5000"),
                txn_time_est=datetime(2024, 9, 1),
                txn_id="c1",
            )
        )
        out_inc = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 3),
            include_cash=True,
        )
        out_exc = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 9, 1),
            end_date=date(2024, 9, 3),
            include_cash=False,
        )
        # With include_cash=true: baseline = cash + stock_cost, mv = cash + stock_mv
        assert out_inc["market_value"][-1] == 5000.0  # cash only, no stocks
        assert out_inc["baseline"][-1] == 5000.0  # cash only, no stocks
        assert out_inc["profit_loss"][-1] == 0.0  # P/L = 0 (no stocks)
        assert out_inc["baseline_label"] == "Book Value (cash + holdings cost)"
        
        # With include_cash=false: baseline = stock_cost, mv = stock_mv
        assert out_exc["market_value"][-1] == 0.0  # no stocks
        assert out_exc["baseline"][-1] == 0.0  # no stocks
        assert out_exc["profit_loss"][-1] == 0.0
        assert out_exc["baseline_label"] == "Holdings Cost (avg)"
        
        assert out_inc["includes_cash"] is True
        assert out_exc["includes_cash"] is False


class TestNetValueCurveResponseShape:
    def test_response_has_columnar_arrays_and_metadata(
        self, net_value_service, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("1"),
                price=Decimal("100"),
                txn_time_est=datetime(2024, 10, 1),
                txn_id="b4",
            )
        )
        out = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 10, 1),
            end_date=date(2024, 10, 5),
        )
        n = len(out["dates"])
        assert n == 5
        assert len(out["baseline"]) == n
        assert len(out["market_value"]) == n
        assert len(out["profit_loss"]) == n
        assert len(out["profit_loss_pct"]) == n
        assert len(out["is_trading_day"]) == n
        assert len(out["last_trading_date"]) == n
        # Default include_cash=True, so should use "Book Value" label
        assert out["baseline_label"] == "Book Value (cash + holdings cost)"
        assert out["price_type"] == "close"


class TestNetValueCurveTransactionDate:
    """Transactions on date T are applied before T's close value."""

    def test_transaction_on_day_reflected_in_that_day_value(
        self, net_value_service, transaction_service, account_for_transactions
    ):
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("50"),
                txn_time_est=datetime(2024, 11, 5, 14, 30, 0),
                txn_id="b5",
            )
        )
        out = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 11, 5),
            end_date=date(2024, 11, 7),
            include_cash=False,  # Stock-only mode for this test
        )
        # On 2024-11-05 we have the position and value
        nov5_idx = next(i for i, d in enumerate(out["dates"]) if d == "2024-11-05")
        assert out["baseline"][nov5_idx] == 500.0  # Stock cost only
        assert out["market_value"][nov5_idx] == 1000.0  # 10*100 mock (stock_mv only, no cash)


class TestNetValueCurveCashDepositRegression:
    """
    Regression test: Depositing cash must NOT change P/L (only changes equity level).
    This test would have caught the bug where include_cash=true didn't add cash to baseline.
    """

    def test_cash_deposit_only_no_profit(
        self, net_value_service, transaction_service, account_for_transactions
    ):
        """
        Simplest case: Just deposit cash, no stocks.
        Expected: baseline = cash, mv = cash, P/L = 0
        """
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("50000"),
                txn_time_est=datetime(2024, 12, 1, 9, 0, 0),
                txn_id="dep0",
            )
        )
        out = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 1),
            include_cash=True,
        )
        assert out["baseline"][0] == 50000.0  # cash only
        assert out["market_value"][0] == 50000.0  # cash only
        assert out["profit_loss"][0] == 0.0  # No profit from just depositing cash

    def test_cash_deposit_does_not_create_fake_profit(
        self, net_value_service, transaction_service, account_for_transactions
    ):
        """
        Scenario:
        - Start: cash deposit $100,000
        - Buy stock: $8,000 worth (80 shares @ $100, price unchanged)
        - End of day: stock price unchanged
        
        Expected:
        - include_cash=false: baseline=8000, mv=8000, P/L=0
        - include_cash=true: baseline=current_cash(92000)+stock_cost(8000)=100000, mv=100000, P/L=0
        Note: After buying, cash = 100000 (deposit) - 8000 (buy cost) = 92000
        """
        # Cash deposit
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("100000"),
                txn_time_est=datetime(2024, 12, 1, 9, 0, 0),
                txn_id="dep1",
            )
        )
        # Buy stock: 80 shares @ $100 = $8,000 (mock price is $100, so cost = $8,000)
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("80"),
                price=Decimal("100"),
                fees=Decimal("0"),
                txn_time_est=datetime(2024, 12, 1, 10, 0, 0),
                txn_id="buy1",
            )
        )
        
        # Test with include_cash=false (stocks-only)
        out_no_cash = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 1),
            include_cash=False,
        )
        assert len(out_no_cash["dates"]) == 1
        assert out_no_cash["baseline"][0] == 8000.0  # stock_cost only
        assert out_no_cash["market_value"][0] == 8000.0  # 80 * 100 (mock price)
        assert out_no_cash["profit_loss"][0] == 0.0  # No P/L when price unchanged
        assert out_no_cash["baseline_label"] == "Holdings Cost (avg)"
        
        # Test with include_cash=true (equity mode)
        out_with_cash = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 12, 1),
            end_date=date(2024, 12, 1),
            include_cash=True,
        )
        assert len(out_with_cash["dates"]) == 1
        # After buy: cash = 100000 - 8000 = 92000, stock_cost = 8000
        # baseline = cash (92000) + stock_cost (8000) = 100000
        # mv = cash (92000) + stock_mv (8000) = 100000
        assert out_with_cash["baseline"][0] == 100000.0
        assert out_with_cash["market_value"][0] == 100000.0
        assert out_with_cash["profit_loss"][0] == 0.0  # P/L should be 0, not ~100k
        assert out_with_cash["baseline_label"] == "Book Value (cash + holdings cost)"
        
        # Verify P/L% is 0 (not some huge percentage)
        assert out_with_cash["profit_loss_pct"][0] == 0.0
        
        # Key invariant: depositing cash and buying stock should NOT create fake profit
        # The P/L is 0 because stock price unchanged, even though we have cash

    def test_sell_stock_into_cash_does_not_change_equity(
        self, net_value_service, transaction_service, account_for_transactions
    ):
        """
        Selling stock into cash must NOT change equity at the moment of sale (ignoring fees),
        and must NOT create fake P/L.
        """
        # Start with cash deposit
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000"),
                txn_time_est=datetime(2024, 12, 2, 9, 0, 0),
                txn_id="dep2",
            )
        )
        # Buy 10 shares @ $100
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("100"),
                fees=Decimal("0"),
                txn_time_est=datetime(2024, 12, 2, 10, 0, 0),
                txn_id="buy2",
            )
        )
        # Sell 10 shares @ $100 (same price, no fees)
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.SELL,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("100"),
                fees=Decimal("0"),
                txn_time_est=datetime(2024, 12, 2, 11, 0, 0),
                txn_id="sell2",
            )
        )
        
        # After sell: cash = 10000 (deposit) + 1000 (sale proceeds) - 1000 (buy cost) = 10000
        # Holdings: 0 shares
        # With include_cash=true: baseline = cash (10000) + stock_cost (0) = 10000
        #                          mv = cash (10000) + stock_mv (0) = 10000
        #                          P/L = 0
        out = net_value_service.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 12, 2),
            end_date=date(2024, 12, 2),
            include_cash=True,
        )
        assert len(out["dates"]) == 1
        # Cash: 10000 (deposit) + 1000 (sale) - 1000 (buy) = 10000
        assert out["baseline"][0] == 10000.0  # cash + stock_cost (0)
        assert out["market_value"][0] == 10000.0  # cash + stock_mv (0)
        assert out["profit_loss"][0] == 0.0  # No fake P/L from selling at cost
