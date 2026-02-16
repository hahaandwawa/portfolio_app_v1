"""
Performance and stress tests for NetValueService with large datasets.
Tests scalability with many transactions, symbols, and date ranges.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
import time

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


@pytest.fixture
def mock_price_svc_large():
    """Mock price service for large datasets - returns $100 for all symbols/dates."""
    def _get(symbols, start, end, refresh=False):
        from datetime import timedelta
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
def net_value_service_large(transaction_service, mock_price_svc_large):
    return NetValueService(
        transaction_service=transaction_service,
        historical_price_service=mock_price_svc_large,
    )


class TestPerformanceLargeDatasets:
    """Performance tests with large numbers of transactions and symbols."""

    def test_many_transactions_single_symbol(
        self, net_value_service_large, transaction_service, account_for_transactions
    ):
        """Many transactions for a single symbol over a year."""
        num_transactions = 100
        start_date = date(2024, 1, 1)
        
        for i in range(num_transactions):
            txn_date = start_date + timedelta(days=i * 3)  # Every 3 days
            if i % 2 == 0:
                # Buy
                transaction_service.create_transaction(
                    make_transaction_create(
                        account_name=account_for_transactions,
                        txn_type=TransactionType.BUY,
                        symbol="AAPL",
                        quantity=Decimal("10"),
                        price=Decimal("100"),
                        txn_time_est=datetime.combine(txn_date, datetime.min.time()),
                        txn_id=f"buy_{i}",
                    )
                )
            else:
                # Sell
                transaction_service.create_transaction(
                    make_transaction_create(
                        account_name=account_for_transactions,
                        txn_type=TransactionType.SELL,
                        symbol="AAPL",
                        quantity=Decimal("5"),
                        price=Decimal("100"),
                        txn_time_est=datetime.combine(txn_date, datetime.min.time()),
                        txn_id=f"sell_{i}",
                    )
                )
        
        start_time = time.time()
        out = net_value_service_large.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=start_date,
            end_date=start_date + timedelta(days=365),
        )
        elapsed = time.time() - start_time
        
        assert len(out["dates"]) == 366  # 365 days + 1
        assert elapsed < 5.0  # Should complete in under 5 seconds
        print(f"Processed {num_transactions} transactions in {elapsed:.2f}s")

    def test_many_symbols_few_transactions(
        self, net_value_service_large, transaction_service, account_for_transactions
    ):
        """Many symbols with few transactions each."""
        num_symbols = 50
        symbols = [f"SYM{i:03d}" for i in range(num_symbols)]
        txn_date = date(2024, 1, 15)
        
        for sym in symbols:
            transaction_service.create_transaction(
                make_transaction_create(
                    account_name=account_for_transactions,
                    txn_type=TransactionType.BUY,
                    symbol=sym,
                    quantity=Decimal("10"),
                    price=Decimal("100"),
                    txn_time_est=datetime.combine(txn_date, datetime.min.time()),
                    txn_id=f"buy_{sym}",
                )
            )
        
        start_time = time.time()
        out = net_value_service_large.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=txn_date,
            end_date=txn_date + timedelta(days=30),
        )
        elapsed = time.time() - start_time
        
        assert len(out["dates"]) == 31
        assert elapsed < 3.0  # Should complete quickly
        print(f"Processed {num_symbols} symbols in {elapsed:.2f}s")

    def test_long_date_range(
        self, net_value_service_large, transaction_service, account_for_transactions
    ):
        """Long date range (multiple years) with transactions."""
        start_date = date(2020, 1, 1)
        end_date = date(2024, 12, 31)
        
        # Add transactions at key points
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000"),
                txn_time_est=datetime.combine(start_date, datetime.min.time()),
                txn_id="start",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.BUY,
                symbol="AAPL",
                quantity=Decimal("100"),
                price=Decimal("100"),
                txn_time_est=datetime.combine(start_date + timedelta(days=100), datetime.min.time()),
                txn_id="buy",
            )
        )
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.SELL,
                symbol="AAPL",
                quantity=Decimal("50"),
                price=Decimal("150"),
                txn_time_est=datetime.combine(end_date - timedelta(days=100), datetime.min.time()),
                txn_id="sell",
            )
        )
        
        start_time = time.time()
        out = net_value_service_large.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=start_date,
            end_date=end_date,
        )
        elapsed = time.time() - start_time
        
        # Should have ~1825 days (5 years)
        assert len(out["dates"]) > 1800
        assert elapsed < 10.0  # Should complete in reasonable time
        print(f"Processed {len(out['dates'])} days in {elapsed:.2f}s")

    def test_daily_transactions_year(
        self, net_value_service_large, transaction_service, account_for_transactions
    ):
        """Daily transactions for a full year."""
        start_date = date(2024, 1, 1)
        end_date = date(2024, 12, 31)
        
        # Add a transaction every trading day (weekdays only)
        current = start_date
        txn_count = 0
        while current <= end_date:
            if current.weekday() < 5:  # Monday-Friday
                transaction_service.create_transaction(
                    make_transaction_create(
                        account_name=account_for_transactions,
                        txn_type=TransactionType.BUY if txn_count % 2 == 0 else TransactionType.SELL,
                        symbol="AAPL",
                        quantity=Decimal("1"),
                        price=Decimal("100"),
                        txn_time_est=datetime.combine(current, datetime.min.time()),
                        txn_id=f"txn_{txn_count}",
                    )
                )
                txn_count += 1
            current += timedelta(days=1)
        
        start_time = time.time()
        out = net_value_service_large.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=start_date,
            end_date=end_date,
        )
        elapsed = time.time() - start_time
        
        assert len(out["dates"]) == 366  # 2024 is leap year
        assert elapsed < 10.0
        print(f"Processed {txn_count} transactions over {len(out['dates'])} days in {elapsed:.2f}s")

    def test_multiple_accounts_many_transactions(
        self, net_value_service_large, transaction_service, account_service, account_for_transactions
    ):
        """Multiple accounts with many transactions each."""
        num_accounts = 5
        from src.service.account_service import AccountCreate
        accounts = [account_for_transactions]
        for i in range(1, num_accounts):
            acc_name = f"Account{i}"
            account_service.save_account(AccountCreate(name=acc_name))
            accounts.append(acc_name)
        
        txn_date = date(2024, 1, 15)
        transactions_per_account = 50
        
        for acc in accounts:
            for i in range(transactions_per_account):
                transaction_service.create_transaction(
                    make_transaction_create(
                        account_name=acc,
                        txn_type=TransactionType.BUY,
                        symbol=f"SYM{i % 10}",  # 10 different symbols per account
                        quantity=Decimal("10"),
                        price=Decimal("100"),
                        txn_time_est=datetime.combine(txn_date + timedelta(days=i), datetime.min.time()),
                        txn_id=f"{acc}_buy_{i}",
                    )
                )
        
        start_time = time.time()
        out = net_value_service_large.get_net_value_curve(
            account_names=accounts,
            start_date=txn_date,
            end_date=txn_date + timedelta(days=transactions_per_account),
        )
        elapsed = time.time() - start_time
        
        assert len(out["dates"]) == transactions_per_account + 1
        assert elapsed < 5.0
        print(f"Processed {num_accounts * transactions_per_account} transactions across {num_accounts} accounts in {elapsed:.2f}s")


class TestPerformanceMemoryUsage:
    """Tests to ensure memory usage is reasonable."""

    def test_large_response_size(
        self, net_value_service_large, transaction_service, account_for_transactions
    ):
        """Test that large responses are generated correctly."""
        start_date = date(2020, 1, 1)
        end_date = date(2024, 12, 31)
        
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000"),
                txn_time_est=datetime.combine(start_date, datetime.min.time()),
                txn_id="deposit",
            )
        )
        
        out = net_value_service_large.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=start_date,
            end_date=end_date,
        )
        
        # Verify all arrays have same length
        num_days = len(out["dates"])
        assert len(out["baseline"]) == num_days
        assert len(out["market_value"]) == num_days
        assert len(out["profit_loss"]) == num_days
        assert len(out["profit_loss_pct"]) == num_days
        assert len(out["is_trading_day"]) == num_days
        assert len(out["last_trading_date"]) == num_days
        
        # Verify data types are correct
        assert all(isinstance(d, str) for d in out["dates"])
        assert all(isinstance(b, (int, float)) for b in out["baseline"])
        assert all(isinstance(mv, (int, float)) for mv in out["market_value"])
        assert all(isinstance(pl, (int, float)) for pl in out["profit_loss"])
        assert all(isinstance(plp, (int, float, type(None))) for plp in out["profit_loss_pct"])
        assert all(isinstance(itd, bool) for itd in out["is_trading_day"])
        assert all(isinstance(ltd, str) for ltd in out["last_trading_date"])


class TestPerformanceConcurrentScenarios:
    """Test scenarios that might occur in production."""

    def test_realistic_portfolio_scenario(
        self, net_value_service_large, transaction_service, account_for_transactions
    ):
        """Simulate a realistic portfolio with various transaction types."""
        # Initial deposit
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("50000"),
                txn_time_est=datetime(2024, 1, 1),
                txn_id="init_deposit",
            )
        )
        
        # Buy multiple positions over time
        symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        buy_dates = [
            date(2024, 1, 15),
            date(2024, 1, 22),
            date(2024, 1, 29),
            date(2024, 2, 5),
            date(2024, 2, 12),
        ]
        for i, sym in enumerate(symbols):
            transaction_service.create_transaction(
                make_transaction_create(
                    account_name=account_for_transactions,
                    txn_type=TransactionType.BUY,
                    symbol=sym,
                    quantity=Decimal("10"),
                    price=Decimal("100"),
                    txn_time_est=datetime.combine(buy_dates[i], datetime.min.time()),
                    txn_id=f"buy_{sym}",
                )
            )
        
        # Some sells
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.SELL,
                symbol="AAPL",
                quantity=Decimal("5"),
                price=Decimal("120"),
                txn_time_est=datetime(2024, 6, 1),
                txn_id="sell_aapl",
            )
        )
        
        # Additional deposits
        transaction_service.create_transaction(
            make_transaction_create(
                account_name=account_for_transactions,
                txn_type=TransactionType.CASH_DEPOSIT,
                cash_amount=Decimal("10000"),
                txn_time_est=datetime(2024, 9, 1),
                txn_id="add_deposit",
            )
        )
        
        start_time = time.time()
        out = net_value_service_large.get_net_value_curve(
            account_names=[account_for_transactions],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        elapsed = time.time() - start_time
        
        assert len(out["dates"]) == 366
        assert elapsed < 2.0
        print(f"Realistic portfolio scenario completed in {elapsed:.2f}s")
        
        # Verify final state
        final_baseline = out["baseline"][-1]
        final_mv = out["market_value"][-1]
        assert final_baseline > 0
        assert final_mv > 0
