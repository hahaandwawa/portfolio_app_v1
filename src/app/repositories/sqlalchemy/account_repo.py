"""SQLAlchemy implementation of AccountRepository."""

from typing import Optional

from sqlalchemy.orm import Session

from app.domain.models import Account
from app.repositories.sqlalchemy.orm_models import AccountORM


class SqlAlchemyAccountRepository:
    """SQLAlchemy-backed account repository."""

    def __init__(self, db: Session):
        self._db = db

    def create(self, account: Account) -> Account:
        """Persist a new account."""
        orm_account = AccountORM(
            account_id=account.account_id,
            name=account.name,
            cost_basis_method=account.cost_basis_method,
            created_at_est=account.created_at_est,
        )
        self._db.add(orm_account)
        self._db.commit()
        self._db.refresh(orm_account)
        return self._to_domain(orm_account)

    def get_by_id(self, account_id: str) -> Optional[Account]:
        """Retrieve account by ID."""
        orm_account = self._db.query(AccountORM).filter(
            AccountORM.account_id == account_id
        ).first()
        return self._to_domain(orm_account) if orm_account else None

    def get_by_name(self, name: str) -> Optional[Account]:
        """Retrieve account by name."""
        orm_account = self._db.query(AccountORM).filter(
            AccountORM.name == name
        ).first()
        return self._to_domain(orm_account) if orm_account else None

    def list_all(self) -> list[Account]:
        """List all accounts."""
        orm_accounts = self._db.query(AccountORM).order_by(AccountORM.name).all()
        return [self._to_domain(a) for a in orm_accounts]

    def update(self, account: Account) -> Account:
        """Update an existing account."""
        orm_account = self._db.query(AccountORM).filter(
            AccountORM.account_id == account.account_id
        ).first()
        if orm_account:
            orm_account.name = account.name
            orm_account.cost_basis_method = account.cost_basis_method
            self._db.commit()
            self._db.refresh(orm_account)
            return self._to_domain(orm_account)
        raise ValueError(f"Account not found: {account.account_id}")

    def delete(self, account_id: str) -> None:
        """Delete an account."""
        self._db.query(AccountORM).filter(
            AccountORM.account_id == account_id
        ).delete()
        self._db.commit()

    @staticmethod
    def _to_domain(orm: AccountORM) -> Account:
        """Convert ORM model to domain model."""
        return Account(
            account_id=orm.account_id,
            name=orm.name,
            cost_basis_method=orm.cost_basis_method,
            created_at_est=orm.created_at_est,
        )
