"""
Unit tests for PortfolioEngine.

Tests cover:
- Rebuild from ledger transactions
- Position calculation after BUY/SELL
- Cash balance calculation
- Handling of deleted transactions
- Multi-account aggregation
- Validation helpers for sell/withdraw
"""

import pytest
from decimal import Decimal
from typing import Callable

from app.services import PortfolioEngine, LedgerService
from app.services.ledger_service import TransactionCreate
from app.domain.models import (
    Account,
    Transaction,
    TransactionType,
    PositionCache,
    CashCache,
)
from app.core.exceptions import NotFoundError

from tests.conftest import (
    eastern_datetime,
    create_buy_transaction_data,
    create_sell_transaction_data,
    create_cash_deposit_data,
    create_cash_withdraw_data,
    assert_decimal_equal,
)


# =============================================================================
# REBUILD TESTS - POSITIONS
# =============================================================================


class TestRebuildPositions:
    """Tests for portfolio position rebuilding."""

    def test_rebuild_empty_account(
        self,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN an account with no transactions
        WHEN I rebuild the account
        THEN get_positions returns empty list
        """
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)

        assert positions == []

    def test_rebuild_after_single_buy(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN an account with one BUY transaction
        WHEN I rebuild the account
        THEN positions reflect the bought shares
        """
        data = create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        ledger_service.add_transaction(data)

        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].shares == Decimal("10")

    def test_rebuild_after_multiple_buys_same_symbol(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN multiple BUY transactions for the same symbol
        WHEN I rebuild
        THEN shares are aggregated
        """
        for qty in [10, 5, 15]:
            data = create_buy_transaction_data(
                account_id=sample_account.account_id,
                symbol="AAPL",
                quantity=Decimal(str(qty)),
                price=Decimal("185.00"),
            )
            ledger_service.add_transaction(data)

        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].shares == Decimal("30")  # 10 + 5 + 15

    def test_rebuild_after_buy_and_partial_sell(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN BUY 10 shares then SELL 3 shares
        WHEN I rebuild
        THEN remaining shares = 7
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        ledger_service.add_transaction(create_sell_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("3"),
            price=Decimal("190.00"),
        ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions) == 1
        assert positions[0].shares == Decimal("7")

    def test_rebuild_sell_to_zero_removes_position(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN BUY 10 shares then SELL all 10 shares
        WHEN I rebuild
        THEN position is removed (not stored with shares=0)
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        ledger_service.add_transaction(create_sell_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("190.00"),
        ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions) == 0

    def test_rebuild_multiple_symbols(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN BUY transactions for multiple symbols
        WHEN I rebuild
        THEN each symbol has its own position
        """
        symbols_quantities = [
            ("AAPL", Decimal("10")),
            ("MSFT", Decimal("5")),
            ("GOOGL", Decimal("8")),
        ]

        for symbol, qty in symbols_quantities:
            ledger_service.add_transaction(create_buy_transaction_data(
                account_id=sample_account.account_id,
                symbol=symbol,
                quantity=qty,
                price=Decimal("100.00"),
            ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions) == 3

        positions_dict = {p.symbol: p.shares for p in positions}
        assert positions_dict["AAPL"] == Decimal("10")
        assert positions_dict["MSFT"] == Decimal("5")
        assert positions_dict["GOOGL"] == Decimal("8")

    def test_rebuild_ignores_deleted_transactions(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN a BUY transaction that was soft deleted
        WHEN I rebuild
        THEN the deleted transaction is ignored
        """
        data = create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        )
        txn = ledger_service.add_transaction(data)
        ledger_service.soft_delete_transaction(txn.txn_id)

        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions) == 0

    def test_rebuild_uses_txn_time_ordering(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN transactions added in non-chronological order
        WHEN I rebuild
        THEN transactions are processed in txn_time_est order
        """
        # Add transactions out of order
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
            txn_time_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))
        ledger_service.add_transaction(create_sell_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("5"),
            price=Decimal("190.00"),
            txn_time_est=eastern_datetime(2024, 1, 20, 10, 0),  # Later
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("3"),
            price=Decimal("188.00"),
            txn_time_est=eastern_datetime(2024, 1, 17, 10, 0),  # Middle
        ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)
        # 10 + 3 - 5 = 8
        assert positions[0].shares == Decimal("8")

    def test_rebuild_nonexistent_account_raises(
        self,
        portfolio_engine: PortfolioEngine,
    ):
        """
        GIVEN no account with specified ID exists
        WHEN I rebuild
        THEN NotFoundError is raised
        """
        with pytest.raises(NotFoundError):
            portfolio_engine.rebuild_account("nonexistent-account")


# =============================================================================
# REBUILD TESTS - CASH
# =============================================================================


class TestRebuildCash:
    """Tests for portfolio cash balance rebuilding."""

    def test_rebuild_empty_account_zero_cash(
        self,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN an account with no transactions
        WHEN I rebuild
        THEN cash balance is $0
        """
        portfolio_engine.rebuild_account(sample_account.account_id)

        cash = portfolio_engine.get_cash_balance(sample_account.account_id)

        assert cash == Decimal("0")

    def test_rebuild_after_deposit(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN a CASH_DEPOSIT of $10,000
        WHEN I rebuild
        THEN cash balance is $10,000
        """
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000.00"),
        ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        cash = portfolio_engine.get_cash_balance(sample_account.account_id)
        assert cash == Decimal("10000.00")

    def test_rebuild_deposit_and_withdrawal(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN CASH_DEPOSIT $10,000 then CASH_WITHDRAW $2,500
        WHEN I rebuild
        THEN cash balance is $7,500
        """
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000.00"),
        ))
        ledger_service.add_transaction(create_cash_withdraw_data(
            account_id=sample_account.account_id,
            amount=Decimal("2500.00"),
        ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        cash = portfolio_engine.get_cash_balance(sample_account.account_id)
        assert cash == Decimal("7500.00")

    def test_rebuild_cash_affected_by_buy(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN CASH_DEPOSIT $10,000 then BUY 10 AAPL @ $185 with $5 fees
        WHEN I rebuild
        THEN cash = 10000 - (10 * 185) - 5 = $8,145
        """
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000.00"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
            fees=Decimal("5.00"),
        ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        cash = portfolio_engine.get_cash_balance(sample_account.account_id)
        expected = Decimal("10000.00") - Decimal("1850.00") - Decimal("5.00")
        assert cash == expected  # $8,145.00

    def test_rebuild_cash_affected_by_sell(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN existing position and SELL 5 AAPL @ $190 with $5 fees
        WHEN I rebuild
        THEN cash increases by (5 * 190) - 5 = $945
        """
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("5000.00"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        ledger_service.add_transaction(create_sell_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("5"),
            price=Decimal("190.00"),
            fees=Decimal("5.00"),
        ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        cash = portfolio_engine.get_cash_balance(sample_account.account_id)
        # 5000 - 1850 + (950 - 5) = 5000 - 1850 + 945 = 4095
        expected = Decimal("4095.00")
        assert cash == expected

    def test_rebuild_cash_can_go_negative(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN no deposit and a BUY transaction
        WHEN I rebuild
        THEN cash balance can be negative (no enforcement in rebuild)
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        cash = portfolio_engine.get_cash_balance(sample_account.account_id)
        assert cash < Decimal("0")


# =============================================================================
# AGGREGATION TESTS
# =============================================================================


class TestAggregation:
    """Tests for multi-account aggregation."""

    def test_aggregate_positions_single_account(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN one account with positions
        WHEN I aggregate
        THEN result matches the account's positions
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.aggregate_positions([sample_account.account_id])

        assert len(positions) == 1
        assert positions[0].symbol == "AAPL"
        assert positions[0].shares == Decimal("10")

    def test_aggregate_positions_multiple_accounts(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        account_factory: Callable,
    ):
        """
        GIVEN Account A has 10 AAPL, Account B has 5 AAPL and 20 MSFT
        WHEN I aggregate
        THEN AAPL=15, MSFT=20
        """
        account_a = account_factory(name="Account A")
        account_b = account_factory(name="Account B")

        # Account A: 10 AAPL
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_a.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(account_a.account_id)

        # Account B: 5 AAPL + 20 MSFT
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_b.account_id,
            symbol="AAPL",
            quantity=Decimal("5"),
            price=Decimal("185.00"),
        ))
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_b.account_id,
            symbol="MSFT",
            quantity=Decimal("20"),
            price=Decimal("375.00"),
        ))
        portfolio_engine.rebuild_account(account_b.account_id)

        positions = portfolio_engine.aggregate_positions([
            account_a.account_id,
            account_b.account_id,
        ])

        positions_dict = {p.symbol: p.shares for p in positions}
        assert positions_dict["AAPL"] == Decimal("15")
        assert positions_dict["MSFT"] == Decimal("20")

    def test_aggregate_positions_empty_list(
        self,
        portfolio_engine: PortfolioEngine,
    ):
        """
        GIVEN empty account list
        WHEN I aggregate
        THEN result is empty
        """
        positions = portfolio_engine.aggregate_positions([])

        assert positions == []

    def test_aggregate_cash_multiple_accounts(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        account_factory: Callable,
    ):
        """
        GIVEN Account A has $5,000, Account B has $3,000
        WHEN I aggregate cash
        THEN result is $8,000
        """
        account_a = account_factory(name="Account A")
        account_b = account_factory(name="Account B")

        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=account_a.account_id,
            amount=Decimal("5000.00"),
        ))
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=account_b.account_id,
            amount=Decimal("3000.00"),
        ))

        portfolio_engine.rebuild_account(account_a.account_id)
        portfolio_engine.rebuild_account(account_b.account_id)

        total_cash = portfolio_engine.aggregate_cash([
            account_a.account_id,
            account_b.account_id,
        ])

        assert total_cash == Decimal("8000.00")

    def test_aggregate_cash_empty_list(
        self,
        portfolio_engine: PortfolioEngine,
    ):
        """
        GIVEN empty account list
        WHEN I aggregate cash
        THEN result is $0
        """
        cash = portfolio_engine.aggregate_cash([])

        assert cash == Decimal("0")


# =============================================================================
# VALIDATION HELPER TESTS
# =============================================================================


class TestValidateSell:
    """Tests for sell validation helper."""

    def test_validate_sell_sufficient_shares(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has 10 AAPL shares
        WHEN I validate sell of 5 shares
        THEN returns True
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        result = portfolio_engine.validate_sell(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("5"),
        )

        assert result is True

    def test_validate_sell_exact_shares(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has 10 AAPL shares
        WHEN I validate sell of exactly 10 shares
        THEN returns True
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        result = portfolio_engine.validate_sell(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
        )

        assert result is True

    def test_validate_sell_insufficient_shares(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has 10 AAPL shares
        WHEN I validate sell of 15 shares
        THEN returns False
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        result = portfolio_engine.validate_sell(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("15"),
        )

        assert result is False

    def test_validate_sell_symbol_not_held(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has AAPL but not MSFT
        WHEN I validate sell of MSFT
        THEN returns False
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        result = portfolio_engine.validate_sell(
            account_id=sample_account.account_id,
            symbol="MSFT",
            quantity=Decimal("5"),
        )

        assert result is False

    def test_validate_sell_empty_account(
        self,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has no positions
        WHEN I validate sell
        THEN returns False
        """
        portfolio_engine.rebuild_account(sample_account.account_id)

        result = portfolio_engine.validate_sell(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("5"),
        )

        assert result is False


class TestValidateWithdrawal:
    """Tests for withdrawal validation helper."""

    def test_validate_withdrawal_sufficient_cash_enforce_true(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has $10,000 cash
        WHEN I validate withdrawal of $5,000 with enforce=True
        THEN returns True
        """
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        result = portfolio_engine.validate_withdrawal(
            account_id=sample_account.account_id,
            amount=Decimal("5000.00"),
            enforce=True,
        )

        assert result is True

    def test_validate_withdrawal_insufficient_cash_enforce_true(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has $1,000 cash
        WHEN I validate withdrawal of $5,000 with enforce=True
        THEN returns False
        """
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("1000.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        result = portfolio_engine.validate_withdrawal(
            account_id=sample_account.account_id,
            amount=Decimal("5000.00"),
            enforce=True,
        )

        assert result is False

    def test_validate_withdrawal_enforce_false_always_true(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has $1,000 cash
        WHEN I validate withdrawal of $5,000 with enforce=False
        THEN returns True (validation bypassed)
        """
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("1000.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        result = portfolio_engine.validate_withdrawal(
            account_id=sample_account.account_id,
            amount=Decimal("5000.00"),
            enforce=False,
        )

        assert result is True

    def test_validate_withdrawal_empty_account_enforce_true(
        self,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has no cash
        WHEN I validate any withdrawal with enforce=True
        THEN returns False
        """
        portfolio_engine.rebuild_account(sample_account.account_id)

        result = portfolio_engine.validate_withdrawal(
            account_id=sample_account.account_id,
            amount=Decimal("100.00"),
            enforce=True,
        )

        assert result is False


# =============================================================================
# FRACTIONAL SHARES TESTS
# =============================================================================


class TestFractionalShares:
    """Tests for fractional share support."""

    def test_fractional_buy(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN a BUY of 0.5 shares
        WHEN I rebuild
        THEN position shows 0.5 shares
        """
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("0.5"),
            price=Decimal("185.00"),
        ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert positions[0].shares == Decimal("0.5")

    def test_fractional_aggregation(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN multiple fractional purchases
        WHEN I rebuild
        THEN fractions are properly summed
        """
        for qty in ["0.33", "0.33", "0.34"]:
            ledger_service.add_transaction(create_buy_transaction_data(
                account_id=sample_account.account_id,
                symbol="AAPL",
                quantity=Decimal(qty),
                price=Decimal("185.00"),
            ))

        portfolio_engine.rebuild_account(sample_account.account_id)

        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert positions[0].shares == Decimal("1.00")
