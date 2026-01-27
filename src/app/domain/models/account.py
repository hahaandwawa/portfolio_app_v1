"""Account domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.models.enums import CostBasisMethod


@dataclass
class Account:
    """
    Investment account container.

    Supports multiple accounts with configurable cost basis methods.
    All operations can be performed on single accounts or aggregated across multiple.
    """

    account_id: str
    name: str
    cost_basis_method: CostBasisMethod = CostBasisMethod.FIFO
    created_at_est: Optional[datetime] = field(default=None)

    def __post_init__(self) -> None:
        if isinstance(self.cost_basis_method, str):
            self.cost_basis_method = CostBasisMethod(self.cost_basis_method)
