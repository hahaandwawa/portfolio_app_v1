"""Portfolio engine for deriving holdings and cash from ledger."""

from collections import defaultdict
from decimal import Decimal
from typing import Optional

from app.core.timezone import now_eastern
from app.core.exceptions import NotFoundError
from app.domain.models import (
    Transaction,
    TransactionType,
    PositionCache,
    CashCache,
)
from app.domain.views import PositionView
from app.repositories.protocols import (
    AccountRepository,
    TransactionRepository,
    CacheRepository,
)


class PortfolioEngine:
    """
    Engine for computing portfolio state from ledger.

    Rebuilds position and cash caches by replaying all transactions.
    Caches are never edited directly; always derived from source of truth (ledger).
    """

    def __init__(
        self,
        account_repo: AccountRepository,
        transaction_repo: TransactionRepository,
        cache_repo: CacheRepository,
    ):
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo
        self._cache_repo = cache_repo

    def rebuild_account(self, account_id: str) -> None:
        """
        Rebuild position and cash caches for an account by replaying ledger.

        This is the authoritative method for deriving portfolio state.
        Called after any transaction add/edit/delete/import.
        """
        account = self._account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account", account_id)

        # Get all active transactions for the account
        transactions = self._transaction_repo.list_by_account(
            account_id=account_id,
            include_deleted=False,
        )

        # Compute positions and cash from scratch
        positions: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        cash_balance = Decimal("0")

        for txn in transactions:
            if txn.txn_type == TransactionType.BUY:
                positions[txn.symbol] += txn.quantity or Decimal("0")
                cash_balance += txn.net_cash_impact

            elif txn.txn_type == TransactionType.SELL:
                positions[txn.symbol] -= txn.quantity or Decimal("0")
                cash_balance += txn.net_cash_impact

            elif txn.txn_type in (TransactionType.CASH_DEPOSIT, TransactionType.CASH_WITHDRAW):
                cash_balance += txn.net_cash_impact

        # Clear existing caches
        self._cache_repo.delete_positions(account_id)
        self._cache_repo.delete_cash(account_id)

        # Write new position caches
        rebuild_time = now_eastern()
        for symbol, shares in positions.items():
            if shares != Decimal("0"):  # Only store non-zero positions
                self._cache_repo.upsert_position(
                    PositionCache(
                        account_id=account_id,
                        symbol=symbol,
                        shares=shares,
                        last_rebuilt_at_est=rebuild_time,
                    )
                )

        # Write new cash cache
        self._cache_repo.upsert_cash(
            CashCache(
                account_id=account_id,
                cash_balance=cash_balance,
                last_rebuilt_at_est=rebuild_time,
            )
        )

    def get_positions(self, account_id: str) -> list[PositionView]:
        """
        Get current holdings for an account.

        Returns positions from cache (call rebuild_account first if stale).
        """
        positions = self._cache_repo.get_positions(account_id)
        return [
            PositionView(
                symbol=p.symbol,
                shares=p.shares,
            )
            for p in positions
        ]

    def get_cash_balance(self, account_id: str) -> Decimal:
        """
        Get current cash balance for an account.

        Returns balance from cache (call rebuild_account first if stale).
        """
        cash = self._cache_repo.get_cash(account_id)
        return cash.cash_balance if cash else Decimal("0")

    def aggregate_positions(self, account_ids: list[str]) -> list[PositionView]:
        """
        Aggregate positions across multiple accounts.

        Combines shares for same symbols across accounts.
        """
        aggregated: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))

        for account_id in account_ids:
            positions = self._cache_repo.get_positions(account_id)
            for p in positions:
                aggregated[p.symbol] += p.shares

        return [
            PositionView(symbol=symbol, shares=shares)
            for symbol, shares in sorted(aggregated.items())
            if shares != Decimal("0")
        ]

    def aggregate_cash(self, account_ids: list[str]) -> Decimal:
        """Aggregate cash balance across multiple accounts."""
        total = Decimal("0")
        for account_id in account_ids:
            cash = self._cache_repo.get_cash(account_id)
            if cash:
                total += cash.cash_balance
        return total

    def validate_sell(
        self,
        account_id: str,
        symbol: str,
        quantity: Decimal,
    ) -> bool:
        """
        Validate that a SELL transaction is allowed.

        Returns True if sufficient shares exist; False otherwise.
        """
        position = self._cache_repo.get_position(account_id, symbol)
        current_shares = position.shares if position else Decimal("0")
        return current_shares >= quantity

    def validate_withdrawal(
        self,
        account_id: str,
        amount: Decimal,
        enforce: bool = False,
    ) -> bool:
        """
        Validate that a cash withdrawal is allowed.

        Returns True if sufficient cash exists or enforce is False.
        """
        if not enforce:
            return True
        cash = self._cache_repo.get_cash(account_id)
        current_cash = cash.cash_balance if cash else Decimal("0")
        return current_cash >= amount
