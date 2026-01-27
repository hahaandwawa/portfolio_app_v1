"""API routers package."""

from app.api.routers.accounts import router as accounts_router
from app.api.routers.transactions import router as transactions_router
from app.api.routers.analysis import router as analysis_router

__all__ = [
    "accounts_router",
    "transactions_router",
    "analysis_router",
]
