"""Cache repository protocol for derived data."""

from typing import Protocol, Optional

from app.domain.models import PositionCache, CashCache


class CacheRepository(Protocol):
    """Interface for position and cash cache data access."""

    # Position cache operations
    def get_positions(self, account_id: str) -> list[PositionCache]:
        """Get all position caches for an account."""
        ...

    def get_position(self, account_id: str, symbol: str) -> Optional[PositionCache]:
        """Get position cache for a specific symbol."""
        ...

    def upsert_position(self, position: PositionCache) -> PositionCache:
        """Insert or update a position cache entry."""
        ...

    def delete_positions(self, account_id: str) -> None:
        """Delete all position caches for an account (for rebuild)."""
        ...

    # Cash cache operations
    def get_cash(self, account_id: str) -> Optional[CashCache]:
        """Get cash cache for an account."""
        ...

    def upsert_cash(self, cash: CashCache) -> CashCache:
        """Insert or update a cash cache entry."""
        ...

    def delete_cash(self, account_id: str) -> None:
        """Delete cash cache for an account (for rebuild)."""
        ...
