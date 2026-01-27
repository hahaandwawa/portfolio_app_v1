"""Dependency injection for FastAPI."""

from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.repositories.sqlalchemy.database import get_db
from app.repositories.sqlalchemy import (
    SqlAlchemyAccountRepository,
    SqlAlchemyTransactionRepository,
    SqlAlchemyCacheRepository,
)
from app.providers.stub_provider import StubMarketDataProvider
from app.services import (
    LedgerService,
    PortfolioEngine,
    MarketDataService,
    AnalysisService,
)
from app.csv import CsvImporter, CsvExporter, CsvTemplateGenerator
from app.config.settings import get_settings


def get_account_repo(db: Session = Depends(get_db)) -> SqlAlchemyAccountRepository:
    """Provide AccountRepository instance."""
    return SqlAlchemyAccountRepository(db)


def get_transaction_repo(db: Session = Depends(get_db)) -> SqlAlchemyTransactionRepository:
    """Provide TransactionRepository instance."""
    return SqlAlchemyTransactionRepository(db)


def get_cache_repo(db: Session = Depends(get_db)) -> SqlAlchemyCacheRepository:
    """Provide CacheRepository instance."""
    return SqlAlchemyCacheRepository(db)


def get_market_provider() -> StubMarketDataProvider:
    """Provide MarketDataProvider instance (stub for offline operation)."""
    return StubMarketDataProvider()


def get_ledger_service(
    account_repo: SqlAlchemyAccountRepository = Depends(get_account_repo),
    transaction_repo: SqlAlchemyTransactionRepository = Depends(get_transaction_repo),
) -> LedgerService:
    """Provide LedgerService instance."""
    return LedgerService(
        account_repo=account_repo,
        transaction_repo=transaction_repo,
    )


def get_portfolio_engine(
    account_repo: SqlAlchemyAccountRepository = Depends(get_account_repo),
    transaction_repo: SqlAlchemyTransactionRepository = Depends(get_transaction_repo),
    cache_repo: SqlAlchemyCacheRepository = Depends(get_cache_repo),
) -> PortfolioEngine:
    """Provide PortfolioEngine instance."""
    return PortfolioEngine(
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        cache_repo=cache_repo,
    )


def get_market_data_service(
    provider: StubMarketDataProvider = Depends(get_market_provider),
) -> MarketDataService:
    """Provide MarketDataService instance."""
    settings = get_settings()
    return MarketDataService(
        provider=provider,
        cache_ttl_seconds=settings.market_data_cache_ttl_seconds,
    )


def get_analysis_service(
    portfolio_engine: PortfolioEngine = Depends(get_portfolio_engine),
    market_data_service: MarketDataService = Depends(get_market_data_service),
) -> AnalysisService:
    """Provide AnalysisService instance."""
    return AnalysisService(
        portfolio_engine=portfolio_engine,
        market_data_service=market_data_service,
    )


def get_csv_importer(
    ledger_service: LedgerService = Depends(get_ledger_service),
    portfolio_engine: PortfolioEngine = Depends(get_portfolio_engine),
) -> CsvImporter:
    """Provide CsvImporter instance."""
    return CsvImporter(
        ledger_service=ledger_service,
        portfolio_engine=portfolio_engine,
    )


def get_csv_exporter(
    ledger_service: LedgerService = Depends(get_ledger_service),
) -> CsvExporter:
    """Provide CsvExporter instance."""
    return CsvExporter(ledger_service=ledger_service)


def get_csv_template_generator() -> CsvTemplateGenerator:
    """Provide CsvTemplateGenerator instance."""
    return CsvTemplateGenerator()
