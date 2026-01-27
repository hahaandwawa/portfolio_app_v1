"""SQLAlchemy implementation of CacheRepository."""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.domain.models import PositionCache, CashCache
from app.repositories.sqlalchemy.orm_models import PositionCacheORM, CashCacheORM


class SqlAlchemyCacheRepository:
    """SQLAlchemy-backed cache repository for derived data."""

    def __init__(self, db: Session):
        self._db = db

    # Position cache operations

    def get_positions(self, account_id: str) -> list[PositionCache]:
        """Get all position caches for an account."""
        orm_positions = (
            self._db.query(PositionCacheORM)
            .filter(PositionCacheORM.account_id == account_id)
            .order_by(PositionCacheORM.symbol)
            .all()
        )
        return [self._position_to_domain(p) for p in orm_positions]

    def get_position(self, account_id: str, symbol: str) -> Optional[PositionCache]:
        """Get position cache for a specific symbol."""
        orm_pos = (
            self._db.query(PositionCacheORM)
            .filter(
                PositionCacheORM.account_id == account_id,
                PositionCacheORM.symbol == symbol,
            )
            .first()
        )
        return self._position_to_domain(orm_pos) if orm_pos else None

    def upsert_position(self, position: PositionCache) -> PositionCache:
        """Insert or update a position cache entry."""
        orm_pos = (
            self._db.query(PositionCacheORM)
            .filter(
                PositionCacheORM.account_id == position.account_id,
                PositionCacheORM.symbol == position.symbol,
            )
            .first()
        )

        if orm_pos:
            orm_pos.shares = position.shares
            orm_pos.last_rebuilt_at_est = position.last_rebuilt_at_est
        else:
            orm_pos = PositionCacheORM(
                account_id=position.account_id,
                symbol=position.symbol,
                shares=position.shares,
                last_rebuilt_at_est=position.last_rebuilt_at_est,
            )
            self._db.add(orm_pos)

        self._db.commit()
        self._db.refresh(orm_pos)
        return self._position_to_domain(orm_pos)

    def delete_positions(self, account_id: str) -> None:
        """Delete all position caches for an account (for rebuild)."""
        self._db.query(PositionCacheORM).filter(
            PositionCacheORM.account_id == account_id
        ).delete()
        self._db.commit()

    # Cash cache operations

    def get_cash(self, account_id: str) -> Optional[CashCache]:
        """Get cash cache for an account."""
        orm_cash = (
            self._db.query(CashCacheORM)
            .filter(CashCacheORM.account_id == account_id)
            .first()
        )
        return self._cash_to_domain(orm_cash) if orm_cash else None

    def upsert_cash(self, cash: CashCache) -> CashCache:
        """Insert or update a cash cache entry."""
        orm_cash = (
            self._db.query(CashCacheORM)
            .filter(CashCacheORM.account_id == cash.account_id)
            .first()
        )

        if orm_cash:
            orm_cash.cash_balance = cash.cash_balance
            orm_cash.last_rebuilt_at_est = cash.last_rebuilt_at_est
        else:
            orm_cash = CashCacheORM(
                account_id=cash.account_id,
                cash_balance=cash.cash_balance,
                last_rebuilt_at_est=cash.last_rebuilt_at_est,
            )
            self._db.add(orm_cash)

        self._db.commit()
        self._db.refresh(orm_cash)
        return self._cash_to_domain(orm_cash)

    def delete_cash(self, account_id: str) -> None:
        """Delete cash cache for an account (for rebuild)."""
        self._db.query(CashCacheORM).filter(
            CashCacheORM.account_id == account_id
        ).delete()
        self._db.commit()

    @staticmethod
    def _position_to_domain(orm: PositionCacheORM) -> PositionCache:
        """Convert ORM position to domain model."""
        return PositionCache(
            account_id=orm.account_id,
            symbol=orm.symbol,
            shares=Decimal(str(orm.shares)) if orm.shares else Decimal("0"),
            last_rebuilt_at_est=orm.last_rebuilt_at_est,
        )

    @staticmethod
    def _cash_to_domain(orm: CashCacheORM) -> CashCache:
        """Convert ORM cash to domain model."""
        return CashCache(
            account_id=orm.account_id,
            cash_balance=Decimal(str(orm.cash_balance)) if orm.cash_balance else Decimal("0"),
            last_rebuilt_at_est=orm.last_rebuilt_at_est,
        )
