"""Account repository protocol."""

from typing import Protocol, Optional

from app.domain.models import Account


class AccountRepository(Protocol):
    """Interface for account data access."""

    def create(self, account: Account) -> Account:
        """Persist a new account."""
        ...

    def get_by_id(self, account_id: str) -> Optional[Account]:
        """Retrieve account by ID."""
        ...

    def get_by_name(self, name: str) -> Optional[Account]:
        """Retrieve account by name."""
        ...

    def list_all(self) -> list[Account]:
        """List all accounts."""
        ...

    def update(self, account: Account) -> Account:
        """Update an existing account."""
        ...

    def delete(self, account_id: str) -> None:
        """Delete an account (hard delete)."""
        ...
