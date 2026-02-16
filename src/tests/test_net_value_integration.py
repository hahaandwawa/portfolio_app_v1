"""
Integration tests for NetValueService with realistic scenarios and simulated data.
Tests complete workflows and data integrity.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import random

import pytest

from src.service.net_value_service import NetValueService
from src.service.historical_price_service import HistoricalPriceService
from src.service.enums import TransactionType
from src.tests.conftest import make_transaction_create


def _date_str(d):
    return d.isoformat()


def _parse_date(s):
    if hasattr(s, "year"):
        return s
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()


class SimulatedPriceService:
    """Simulates realistic price movements with trends and volatility."""
    
    def __init__(self, initial_prices=None, volatility=0.02, trend=0.0001):
        """
        initial_prices: dict symbol -> initial price
        volatility: daily price volatility (std dev as fraction)
        trend: daily trend (fractional change per day)
        """
        self._initial_prices = initial_prices or {}
        self._volatility = volatility
        self._trend = trend
        self._prices_cache = {}
    
    def get_historical_prices(self, symbols, start_date, end_date, refresh=False):
        from datetime import timedelta
        start = _parse_date(start_date)
        end = _parse_date(end_date)
        result = {}
        
        for sym in symbols:
            if sym not in self._prices_cache:
                # Initialize price for this symbol
                initial = self._initial_prices.get(sym, 100.0)
                self._prices_cache[sym] = {}
                current_price = initial
                d = start
                while d <= end:
                    date_s = _date_str(d)
                    # Random walk with trend
                    change = random.gauss(self._trend, self._volatility)
                    current_price = max(0.01, current_price * (1 + change))  # Prevent negative prices
                    self._prices_cache[sym][date_s] = current_price
                    d += timedelta(days=1)
            
            # Build series from cache
            out = []
            d = start
            last_price = None
            last_trading = None
            while d <= end:
                date_s = _date_str(d)
                price = self._prices_cache[sym].get(date_s)
                if price is not None:
                    last_price = price
                    last_trading = date_s
                out.append({
                    "date": date_s,
                    "close": last_price,
                    "last_trading_date": last_trading or date_s,
                })
                d += timedelta(days=1)
            result[sym] = out
        
        return result


@pytest.fixture
def simulated_price_svc():
    """Price service with simulated realistic price movements."""
    initial_prices = {
        "AAPL": 150.0,
        "MSFT": 300.0,
        "GOOGL": 2500.0,
        "AMZN": 150.0,
        "TSLA": 200.0,
    }
    return SimulatedPriceService(initial_prices=initial_prices, volatility=0.02, trend=0.0001)


@pytest.fixture
def net_value_service_sim(transaction_service, simulated_price_svc):
    return NetValueService(
        transaction_service=transaction_service,
        historical_price_service=simulated_price_svc,
    )


class TestIntegrationRealisticScenarios:
    """Integration tests with realistic trading scenarios."""

    def test_dca_strategy(
        self, net_value_service_sim, transaction_service, account_for_transactions
    ):
        """Dollar Cost Averaging: regular purchases over time."""
        # Initial deposit
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000"),
                txn_time_est=datetime(2024, 1, 1),
                txn_id="deposit",
            )
        )
        
        # Buy $1000 worth every month (use 15th, or last day of month if < 15 days)
        for month in range(1, 13):
            try:
                txn_date = datetime(2024, month, 15)
            except ValueError:
                # Month has < 15 days (shouldn't happen, but be safe)
                import calendar
                last_day = calendar.monthrange(2024, month)[1]
                txn_date = datetime(2024, month, last_day)
            # Approximate: buy ~6.67 shares at $150
            transaction_service.create_transaction(
                make_transaction_create(
                    account_name=account_for_transactions,
                    txn_type=TransactionType.BUY,
                    symbol="AAPL",
                    quantity=Decimal("6.67"),
                    price=Decimal("150"),
                    txn_time_est=txn_date,
                    txn_id=f"dca_{month}",
                )
            )
        
        out = net_value_service_sim.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            include_cash=True,
        )
        
        # Verify we have data for all days
        assert len(out["dates"]) == 366
        
        # Baseline should increase over time (more shares purchased)
        # Note: With include_cash=True, baseline includes cash which decreases as we buy
        # So we check stock-only baseline or verify total equity increases
        out_stocks_only = net_value_service_sim.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            include_cash=False,
        )
        assert out_stocks_only["baseline"][-1] > out_stocks_only["baseline"][0]
        
        # Market value should reflect price movements
        assert all(mv >= 0 for mv in out["market_value"])

    def test_rebalancing_strategy(
        self, net_value_service_sim, transaction_service, account_for_transactions
    ):
        """Portfolio rebalancing: buy/sell to maintain target allocation."""
        # Initial deposit
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("50000"),
                txn_time_est=datetime(2024, 1, 1),
                txn_id="deposit",
            )
        )
        
        # Initial positions: equal weight
        symbols = ["AAPL", "MSFT", "GOOGL"]
        for sym in symbols:
            transaction_service.create_transaction(
                make_transaction_create(
                    account_name=account_for_transactions,
                    txn_type=TransactionType.BUY,
                    symbol=sym,
                    quantity=Decimal("10"),
                    price=Decimal("100"),
                    txn_time_est=datetime(2024, 1, 15),
                    txn_id=f"init_{sym}",
                )
            )
        
        # Rebalance quarterly: sell winners, buy losers
        rebalance_dates = [
            datetime(2024, 4, 1),
            datetime(2024, 7, 1),
            datetime(2024, 10, 1),
        ]
        
        for rebal_date in rebalance_dates:
            # Sell some AAPL
            transaction_service.create_transaction(
                make_transaction_create(
                    account_name=account_for_transactions,
                    txn_type=TransactionType.SELL,
                    symbol="AAPL",
                    quantity=Decimal("2"),
                    price=Decimal("160"),
                    txn_time_est=rebal_date,
                    txn_id=f"rebal_sell_aapl_{rebal_date.month}",
                )
            )
            # Buy more MSFT
            transaction_service.create_transaction(
                make_transaction_create(
                    account_name=account_for_transactions,
                    txn_type=TransactionType.BUY,
                    symbol="MSFT",
                    quantity=Decimal("5"),
                    price=Decimal("320"),
                    txn_time_est=rebal_date,
                    txn_id=f"rebal_buy_msft_{rebal_date.month}",
                )
            )
        
        out = net_value_service_sim.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            include_cash=True,
        )
        
        # Verify curve is continuous
        assert len(out["dates"]) == 366
        assert all(out["dates"][i] < out["dates"][i+1] for i in range(len(out["dates"])-1))
        
        # Verify baseline and market value are consistent
        for i in range(len(out["dates"])):
            baseline = out["baseline"][i]
            mv = out["market_value"][i]
            pl = out["profit_loss"][i]
            assert abs(pl - (mv - baseline)) < 0.01  # P/L = MV - Baseline

    def test_tax_loss_harvesting(
        self, net_value_service_sim, transaction_service, account_for_transactions
    ):
        """Tax loss harvesting: sell losers, buy similar positions."""
        # Initial deposit
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("20000"),
                txn_time_est=datetime(2024, 1, 1),
                txn_id="deposit",
            )
        )
        
        # Buy position that goes down
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="TSLA",
                quantity=Decimal("50"),
                price=Decimal("200"),
                txn_time_est=datetime(2024, 1, 15),
                txn_id="buy_tsla",
            )
        )
        
        # Harvest loss: sell at lower price
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.SELL,
                symbol="TSLA",
                quantity=Decimal("50"),
                price=Decimal("180"),  # Loss of $20/share
                txn_time_est=datetime(2024, 6, 15),
                txn_id="harvest_loss",
            )
        )
        
        # Buy similar position (different symbol)
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AMZN",
                quantity=Decimal("50"),
                price=Decimal("150"),
                txn_time_est=datetime(2024, 6, 16),
                txn_id="buy_amzn",
            )
        )
        
        out = net_value_service_sim.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            include_cash=False,  # Focus on stock P/L
        )
        
        # After harvesting, baseline should reset (sold all TSLA)
        # Then new baseline from AMZN purchase
        june_15_idx = next(i for i, d in enumerate(out["dates"]) if d == "2024-06-15")
        june_16_idx = next(i for i, d in enumerate(out["dates"]) if d == "2024-06-16")
        
        # After sell: baseline should drop to 0 (all sold)
        assert out["baseline"][june_15_idx] == 0.0
        
        # After buy: new baseline
        assert out["baseline"][june_16_idx] > 0


class TestIntegrationDataIntegrity:
    """Tests to ensure data integrity and consistency."""

    def test_pl_equals_mv_minus_baseline(
        self, net_value_service_sim, transaction_service, account_for_transactions
    ):
        """P/L should always equal market_value - baseline."""
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000"),
                txn_time_est=datetime(2024, 1, 1),
                txn_id="deposit",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("150"),
                txn_time_est=datetime(2024, 1, 15),
                txn_id="buy",
            )
        )
        
        for include_cash in [True, False]:
            out = net_value_service_sim.get_net_value_curve(
                account_names=[account_for_transactions],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
                include_cash=include_cash,
            )
            
            for i in range(len(out["dates"])):
                baseline = out["baseline"][i]
                mv = out["market_value"][i]
                pl = out["profit_loss"][i]
                assert abs(pl - (mv - baseline)) < 0.01, f"Day {i}: P/L={pl}, MV={mv}, Baseline={baseline}"

    def test_pl_percent_calculation(
        self, net_value_service_sim, transaction_service, account_for_transactions
    ):
        """P/L% should equal (P/L / baseline) * 100 when baseline > 0."""
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("100"),
                txn_time_est=datetime(2024, 1, 15),
                txn_id="buy",
            )
        )
        
        out = net_value_service_sim.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 31),
            include_cash=False,
        )
        
        for i in range(len(out["dates"])):
            baseline = out["baseline"][i]
            pl = out["profit_loss"][i]
            plpct = out["profit_loss_pct"][i]
            
            if baseline > 0:
                expected_pct = (pl / baseline) * 100
                assert abs(plpct - expected_pct) < 0.01, f"Day {i}: P/L%={plpct}, expected={expected_pct}"
            else:
                assert plpct is None, f"Day {i}: P/L% should be None when baseline=0"

    def test_baseline_monotonic_with_buys(
        self, net_value_service_sim, transaction_service, account_for_transactions
    ):
        """Baseline should only increase (or stay same) when only buying."""
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000"),
                txn_time_est=datetime(2024, 1, 1),
                txn_id="deposit",
            )
        )
        
        # Multiple buys over time (every ~30 days)
        buy_dates = [
            date(2024, 1, 15),
            date(2024, 2, 14),
            date(2024, 3, 16),
            date(2024, 4, 15),
            date(2024, 5, 15),
        ]
        for i, buy_date in enumerate(buy_dates):
            transaction_service.create_transaction(
                make_transaction_create(
                    account_name=account_for_transactions,
                    txn_type=TransactionType.BUY,
                    symbol="AAPL",
                    quantity=Decimal("10"),
                    price=Decimal("150"),
                    txn_time_est=datetime.combine(buy_date, datetime.min.time()),
                    txn_id=f"buy_{i}",
                )
            )
        
        out = net_value_service_sim.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 6, 30),
            include_cash=False,
        )
        
        # Baseline should be non-decreasing (can stay same or increase)
        for i in range(1, len(out["baseline"])):
            assert out["baseline"][i] >= out["baseline"][i-1] - 0.01, \
                f"Baseline decreased: day {i-1}={out['baseline'][i-1]}, day {i}={out['baseline'][i]}"

    def test_cash_consistency(
        self, net_value_service_sim, transaction_service, account_for_transactions
    ):
        """Cash balance should be consistent between include_cash=true and false."""
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000"),
                txn_time_est=datetime(2024, 1, 1),
                txn_id="deposit",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("10"),
                price=Decimal("150"),
                txn_time_est=datetime(2024, 1, 15),
                txn_id="buy",
            )
        )
        
        # Query from deposit date to include all transactions
        out_true = net_value_service_sim.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 1),  # Start from deposit date
            end_date=date(2024, 1, 15),
            include_cash=True,
        )
        out_false = net_value_service_sim.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 1),  # Start from deposit date
            end_date=date(2024, 1, 15),
            include_cash=False,
        )
        
        # Check final day (after buy)
        final_idx = len(out_true["dates"]) - 1
        
        # With include_cash=True: baseline = cash + stock_cost
        # With include_cash=False: baseline = stock_cost only
        # Difference = cash balance
        cash_from_baseline_diff = out_true["baseline"][final_idx] - out_false["baseline"][final_idx]
        cash_from_mv_diff = out_true["market_value"][final_idx] - out_false["market_value"][final_idx]
        expected_cash = 10000.0 - 1500.0  # deposit - buy cost
        
        # Both differences should equal cash balance
        assert abs(cash_from_baseline_diff - expected_cash) < 0.01, \
            f"Baseline diff cash mismatch: got {cash_from_baseline_diff}, expected {expected_cash}"
        assert abs(cash_from_mv_diff - expected_cash) < 0.01, \
            f"MV diff cash mismatch: got {cash_from_mv_diff}, expected {expected_cash}"


class TestIntegrationComplexScenarios:
    """Complex multi-step scenarios."""

    def test_full_trading_year(
        self, net_value_service_sim, transaction_service, account_for_transactions
    ):
        """Simulate a full year of trading activity."""
        # Start of year deposit
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("50000"),
                txn_time_est=datetime(2024, 1, 1),
                txn_id="year_start",
            )
        )
        
        # Build diversified portfolio
        portfolio = {
            "AAPL": {"target": 20, "bought": 0},
            "MSFT": {"target": 15, "bought": 0},
            "GOOGL": {"target": 10, "bought": 0},
            "AMZN": {"target": 15, "bought": 0},
        }
        
        # Buy initial positions
        for sym, info in portfolio.items():
            qty = info["target"]
            transaction_service.create_transaction(
                make_transaction_create(
                    account_name=account_for_transactions,
                    txn_type=TransactionType.BUY,
                    symbol=sym,
                    quantity=Decimal(str(qty)),
                    price=Decimal("100"),
                    txn_time_est=datetime(2024, 1, 15),
                    txn_id=f"init_{sym}",
                )
            )
            info["bought"] = qty
        
        # Mid-year: rebalance
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.SELL,
                symbol="AAPL",
                quantity=Decimal("5"),
                price=Decimal("160"),
                txn_time_est=datetime(2024, 6, 15),
                txn_id="rebal_sell",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="MSFT",
                quantity=Decimal("10"),
                price=Decimal("320"),
                txn_time_est=datetime(2024, 6, 16),
                txn_id="rebal_buy",
            )
        )
        
        # End of year: additional deposit
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000"),
                txn_time_est=datetime(2024, 12, 1),
                txn_id="year_end_deposit",
            )
        )
        
        out = net_value_service_sim.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            include_cash=True,
        )
        
        # Verify complete year
        assert len(out["dates"]) == 366
        
        # Verify data integrity
        for i in range(len(out["dates"])):
            assert out["baseline"][i] >= 0
            assert out["market_value"][i] >= 0
            assert abs(out["profit_loss"][i] - (out["market_value"][i] - out["baseline"][i])) < 0.01
