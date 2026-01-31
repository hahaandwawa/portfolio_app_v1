"""Application context for in-process service management.

Provides a centralized way to access all services without HTTP.
Used by the desktop UI to interact with the backend directly.
"""

from pathlib import Path
from typing import Optional

from app.config.settings import Settings, set_settings, get_settings
from app.repositories.sqlalchemy.database import (
    init_db_with_path,
    reset_database,
    get_session,
)
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


class AppContext:
    """
    Application context providing in-process access to all services.

    This is the main entry point for the desktop UI to interact with
    the backend without going through HTTP/FastAPI.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize application context.

        Args:
            data_dir: Optional data directory. If not provided, uses default.
        """
        self._data_dir = data_dir
        self._session = None
        self._initialized = False

        # Service instances (lazy initialized)
        self._ledger_service: Optional[LedgerService] = None
        self._portfolio_engine: Optional[PortfolioEngine] = None
        self._market_data_service: Optional[MarketDataService] = None
        self._analysis_service: Optional[AnalysisService] = None
        self._csv_importer: Optional[CsvImporter] = None
        self._csv_exporter: Optional[CsvExporter] = None
        self._csv_template: Optional[CsvTemplateGenerator] = None

    def initialize(self, data_dir: Optional[Path] = None) -> None:
        """
        Initialize or reinitialize the application with a data directory.

        Args:
            data_dir: Data directory path. Uses default if not provided.
        """
        if data_dir:
            self._data_dir = data_dir

        # Update global settings
        settings = Settings(data_dir=self._data_dir)
        set_settings(settings)

        # Reset and reinitialize database
        reset_database()
        db_path = settings.get_data_dir() / "investment.db"
        init_db_with_path(db_path)

        # Reset service instances to force recreation
        self._session = None
        self._ledger_service = None
        self._portfolio_engine = None
        self._market_data_service = None
        self._analysis_service = None
        self._csv_importer = None
        self._csv_exporter = None

        self._initialized = True

    @property
    def is_initialized(self) -> bool:
        """Check if context is initialized."""
        return self._initialized

    @property
    def data_dir(self) -> Path:
        """Get the current data directory."""
        return get_settings().get_data_dir()

    def _get_session(self):
        """Get or create database session."""
        if self._session is None:
            self._session = get_session()
        return self._session

    def refresh_session(self) -> None:
        """Refresh the database session (call after external changes)."""
        if self._session:
            self._session.close()
        self._session = get_session()
        # Reset services to use new session
        self._ledger_service = None
        self._portfolio_engine = None
        self._analysis_service = None
        self._csv_importer = None
        self._csv_exporter = None

    # Repository accessors
    def _get_account_repo(self) -> SqlAlchemyAccountRepository:
        return SqlAlchemyAccountRepository(self._get_session())

    def _get_transaction_repo(self) -> SqlAlchemyTransactionRepository:
        return SqlAlchemyTransactionRepository(self._get_session())

    def _get_cache_repo(self) -> SqlAlchemyCacheRepository:
        return SqlAlchemyCacheRepository(self._get_session())

    # Service accessors
    @property
    def ledger(self) -> LedgerService:
        """Get the LedgerService instance."""
        if self._ledger_service is None:
            self._ledger_service = LedgerService(
                account_repo=self._get_account_repo(),
                transaction_repo=self._get_transaction_repo(),
            )
        return self._ledger_service

    @property
    def portfolio(self) -> PortfolioEngine:
        """Get the PortfolioEngine instance."""
        if self._portfolio_engine is None:
            self._portfolio_engine = PortfolioEngine(
                account_repo=self._get_account_repo(),
                transaction_repo=self._get_transaction_repo(),
                cache_repo=self._get_cache_repo(),
            )
        return self._portfolio_engine

    @property
    def market_data(self) -> MarketDataService:
        """Get the MarketDataService instance."""
        if self._market_data_service is None:
            settings = get_settings()
            provider = StubMarketDataProvider()
            self._market_data_service = MarketDataService(
                provider=provider,
                cache_ttl_seconds=settings.market_data_cache_ttl_seconds,
            )
        return self._market_data_service

    @property
    def analysis(self) -> AnalysisService:
        """Get the AnalysisService instance."""
        if self._analysis_service is None:
            self._analysis_service = AnalysisService(
                portfolio_engine=self.portfolio,
                market_data_service=self.market_data,
            )
        return self._analysis_service

    # CSV utilities
    @property
    def csv_importer(self) -> CsvImporter:
        """Get the CsvImporter instance."""
        if self._csv_importer is None:
            self._csv_importer = CsvImporter(
                ledger_service=self.ledger,
                portfolio_engine=self.portfolio,
            )
        return self._csv_importer

    @property
    def csv_exporter(self) -> CsvExporter:
        """Get the CsvExporter instance."""
        if self._csv_exporter is None:
            self._csv_exporter = CsvExporter(ledger_service=self.ledger)
        return self._csv_exporter

    @property
    def csv_template(self) -> CsvTemplateGenerator:
        """Get the CsvTemplateGenerator instance."""
        if self._csv_template is None:
            self._csv_template = CsvTemplateGenerator()
        return self._csv_template

    def close(self) -> None:
        """Clean up resources."""
        if self._session:
            self._session.close()
            self._session = None


# Global application context (singleton for desktop app)
_app_context: Optional[AppContext] = None


def get_app_context() -> AppContext:
    """Get or create the global application context."""
    global _app_context
    if _app_context is None:
        _app_context = AppContext()
    return _app_context


def set_app_context(context: AppContext) -> None:
    """Set the global application context."""
    global _app_context
    _app_context = context
