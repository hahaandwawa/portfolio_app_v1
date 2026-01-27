"""
Integration tests for portfolio rebuild triggers.

Tests cover:
- Rebuild after transaction add/edit/delete
- Full transaction lifecycle with rebuild
- Consistency between ledger and cache
"""

import pytest
from decimal import Decimal
from typing import Callable

from app.services import LedgerService, PortfolioEngine
from app.services.ledger_service import TransactionCreate, TransactionUpdate
from app.domain.models import Account, TransactionType

from tests.conftest import (
    eastern_datetime,
    create_buy_transaction_data,
    create_sell_transaction_data,
    create_cash_deposit_data,
    create_cash_withdraw_data,
    assert_decimal_equal,
)


# =============================================================================
# REBUILD AFTER TRANSACTION ADD
# =============================================================================


class TestRebuildAfterAdd:
    """Tests for rebuild triggered after adding transactions."""

    def test_rebuild_after_buy_updates_positions(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN an empty account
        WHEN I add a BUY and rebuild
        THEN positions reflect the purchase
        """
        # Initial state - no positions
        portfolio_engine.rebuild_account(sample_account.account_id)
        positions_before = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions_before) == 0

        # Add BUY transaction
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))

        # Rebuild
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions_after = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions_after) == 1
        assert positions_after[0].symbol == "AAPL"
        assert positions_after[0].shares == Decimal("10")

    def test_rebuild_after_cash_deposit_updates_balance(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN an empty account
        WHEN I add CASH_DEPOSIT and rebuild
        THEN cash balance is updated
        """
        portfolio_engine.rebuild_account(sample_account.account_id)
        cash_before = portfolio_engine.get_cash_balance(sample_account.account_id)
        assert cash_before == Decimal("0")

        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        cash_after = portfolio_engine.get_cash_balance(sample_account.account_id)
        assert cash_after == Decimal("10000.00")


# =============================================================================
# REBUILD AFTER TRANSACTION EDIT
# =============================================================================


class TestRebuildAfterEdit:
    """Tests for rebuild triggered after editing transactions."""

    def test_rebuild_after_edit_quantity(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has a BUY transaction
        WHEN I edit quantity and rebuild
        THEN positions reflect the new quantity
        """
        # Create initial transaction
        txn = ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions_before = portfolio_engine.get_positions(sample_account.account_id)
        assert positions_before[0].shares == Decimal("10")

        # Edit quantity
        patch = TransactionUpdate(quantity=Decimal("15"))
        ledger_service.edit_transaction(txn.txn_id, patch)
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions_after = portfolio_engine.get_positions(sample_account.account_id)
        assert positions_after[0].shares == Decimal("15")

    def test_rebuild_after_edit_price_affects_cash(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has a BUY transaction
        WHEN I edit price and rebuild
        THEN cash balance reflects new price
        """
        # Deposit cash first
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000.00"),
        ))

        # Create BUY at $185
        txn = ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        # Cash = 10000 - 1850 = 8150
        cash_before = portfolio_engine.get_cash_balance(sample_account.account_id)
        assert_decimal_equal(cash_before, Decimal("8150.00"))

        # Edit price to $190
        patch = TransactionUpdate(price=Decimal("190.00"))
        ledger_service.edit_transaction(txn.txn_id, patch)
        portfolio_engine.rebuild_account(sample_account.account_id)

        # Cash = 10000 - 1900 = 8100
        cash_after = portfolio_engine.get_cash_balance(sample_account.account_id)
        assert_decimal_equal(cash_after, Decimal("8100.00"))


# =============================================================================
# REBUILD AFTER TRANSACTION DELETE
# =============================================================================


class TestRebuildAfterDelete:
    """Tests for rebuild triggered after deleting transactions."""

    def test_rebuild_after_delete_removes_position(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has a BUY transaction
        WHEN I soft delete it and rebuild
        THEN position is removed
        """
        txn = ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions_before = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions_before) == 1

        # Soft delete
        ledger_service.soft_delete_transaction(txn.txn_id)
        portfolio_engine.rebuild_account(sample_account.account_id)

        positions_after = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions_after) == 0

    def test_rebuild_after_delete_restores_cash(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN account has cash deposit then BUY
        WHEN I delete the BUY and rebuild
        THEN cash is restored to pre-buy amount
        """
        # Deposit cash
        ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)
        cash_after_deposit = portfolio_engine.get_cash_balance(sample_account.account_id)

        # BUY reduces cash
        txn = ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)
        cash_after_buy = portfolio_engine.get_cash_balance(sample_account.account_id)
        assert cash_after_buy < cash_after_deposit

        # Delete BUY restores cash
        ledger_service.soft_delete_transaction(txn.txn_id)
        portfolio_engine.rebuild_account(sample_account.account_id)

        cash_after_delete = portfolio_engine.get_cash_balance(sample_account.account_id)
        assert cash_after_delete == cash_after_deposit


# =============================================================================
# FULL TRANSACTION LIFECYCLE
# =============================================================================


class TestFullTransactionLifecycle:
    """Tests for complete transaction lifecycle with rebuilds."""

    def test_full_lifecycle_with_revisions(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        transaction_repo,
        sample_account: Account,
    ):
        """
        GIVEN a fresh account
        WHEN I perform: deposit, buy, edit, sell, delete sell
        THEN all revisions exist and positions are correct
        """
        # 1. CASH_DEPOSIT $10,000
        deposit = ledger_service.add_transaction(create_cash_deposit_data(
            account_id=sample_account.account_id,
            amount=Decimal("10000"),
            txn_time_est=eastern_datetime(2024, 1, 15, 10, 0),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        # 2. BUY 10 AAPL @ $185
        buy = ledger_service.add_transaction(create_buy_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
            txn_time_est=eastern_datetime(2024, 1, 15, 14, 0),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        # Check positions: 10 AAPL
        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert len(positions) == 1
        assert positions[0].shares == Decimal("10")

        # 3. EDIT BUY to change price to $186
        patch = TransactionUpdate(price=Decimal("186.00"))
        ledger_service.edit_transaction(buy.txn_id, patch)
        portfolio_engine.rebuild_account(sample_account.account_id)

        # 4. SELL 5 AAPL @ $190
        sell = ledger_service.add_transaction(create_sell_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("5"),
            price=Decimal("190.00"),
            txn_time_est=eastern_datetime(2024, 1, 20, 14, 0),
        ))
        portfolio_engine.rebuild_account(sample_account.account_id)

        # Check positions: 5 AAPL
        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert positions[0].shares == Decimal("5")

        # 5. SOFT DELETE the SELL
        ledger_service.soft_delete_transaction(sell.txn_id)
        portfolio_engine.rebuild_account(sample_account.account_id)

        # Positions back to 10 AAPL (sell is deleted)
        positions = portfolio_engine.get_positions(sample_account.account_id)
        assert positions[0].shares == Decimal("10")

        # Verify revisions exist
        deposit_revs = transaction_repo.list_revisions_by_txn(deposit.txn_id)
        assert len(deposit_revs) == 1  # CREATE

        buy_revs = transaction_repo.list_revisions_by_txn(buy.txn_id)
        assert len(buy_revs) == 2  # CREATE + UPDATE

        sell_revs = transaction_repo.list_revisions_by_txn(sell.txn_id)
        assert len(sell_revs) == 2  # CREATE + SOFT_DELETE

    def test_multi_account_rebuild_independence(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        account_factory: Callable,
    ):
        """
        GIVEN two accounts with separate transactions
        WHEN I rebuild one account
        THEN the other account is not affected
        """
        account_a = account_factory(name="Account A")
        account_b = account_factory(name="Account B")

        # Add to Account A
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_a.account_id,
            symbol="AAPL",
            quantity=Decimal("10"),
            price=Decimal("185.00"),
        ))
        portfolio_engine.rebuild_account(account_a.account_id)

        # Add to Account B
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_b.account_id,
            symbol="MSFT",
            quantity=Decimal("5"),
            price=Decimal("375.00"),
        ))
        portfolio_engine.rebuild_account(account_b.account_id)

        # Verify independence
        positions_a = portfolio_engine.get_positions(account_a.account_id)
        positions_b = portfolio_engine.get_positions(account_b.account_id)

        assert len(positions_a) == 1
        assert positions_a[0].symbol == "AAPL"

        assert len(positions_b) == 1
        assert positions_b[0].symbol == "MSFT"

        # Rebuild A shouldn't affect B
        ledger_service.add_transaction(create_buy_transaction_data(
            account_id=account_a.account_id,
            symbol="GOOGL",
            quantity=Decimal("8"),
            price=Decimal("140.00"),
        ))
        portfolio_engine.rebuild_account(account_a.account_id)

        positions_b_after = portfolio_engine.get_positions(account_b.account_id)
        assert len(positions_b_after) == 1
        assert positions_b_after[0].symbol == "MSFT"


# =============================================================================
# CONSISTENCY TESTS
# =============================================================================


class TestCacheConsistency:
    """Tests for consistency between ledger and cache."""

    def test_cache_matches_ledger_after_multiple_operations(
        self,
        ledger_service: LedgerService,
        portfolio_engine: PortfolioEngine,
        sample_account: Account,
    ):
        """
        GIVEN multiple add/edit/delete operations
        WHEN I rebuild
        THEN cache exactly matches what ledger transactions would produce
        """
        # Series of operations
        txns = []

        # Add deposits
        for amount in [10000, 5000, 2500]:
            txn = ledger_service.add_transaction(create_cash_deposit_data(
                account_id=sample_account.account_id,
                amount=Decimal(str(amount)),
            ))
            txns.append(txn)

        # Add buys
        for symbol, qty, price in [("AAPL", 10, 185), ("MSFT", 5, 375), ("AAPL", 5, 188)]:
            txn = ledger_service.add_transaction(create_buy_transaction_data(
                account_id=sample_account.account_id,
                symbol=symbol,
                quantity=Decimal(str(qty)),
                price=Decimal(str(price)),
            ))
            txns.append(txn)

        # Sell some
        txn = ledger_service.add_transaction(create_sell_transaction_data(
            account_id=sample_account.account_id,
            symbol="AAPL",
            quantity=Decimal("7"),
            price=Decimal("190.00"),
        ))
        txns.append(txn)

        # Delete one of the buys
        ledger_service.soft_delete_transaction(txns[4].txn_id)  # Second AAPL buy

        # Withdraw some cash
        ledger_service.add_transaction(create_cash_withdraw_data(
            account_id=sample_account.account_id,
            amount=Decimal("1000"),
        ))

        # Rebuild
        portfolio_engine.rebuild_account(sample_account.account_id)

        # Verify cache state
        positions = portfolio_engine.get_positions(sample_account.account_id)
        cash = portfolio_engine.get_cash_balance(sample_account.account_id)

        positions_dict = {p.symbol: p.shares for p in positions}

        # Expected:
        # AAPL: bought 10 (second buy deleted) - sold 7 = 3
        # MSFT: bought 5
        assert positions_dict["AAPL"] == Decimal("3")
        assert positions_dict["MSFT"] == Decimal("5")

        # Cash calculation:
        # +10000 + 5000 + 2500 = 17500
        # -1850 (AAPL buy) - 1875 (MSFT buy) = 13775
        # +1330 (sell 7@190) = 15105
        # -1000 (withdraw) = 14105
        expected_cash = Decimal("14105")
        assert_decimal_equal(cash, expected_cash)
