"""Database connection and session management."""

from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from app.config.settings import get_settings

Base = declarative_base()

# Module-level database state (can be reconfigured at runtime)
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.get_database_url(),
            connect_args={"check_same_thread": False},  # SQLite-specific
            echo=False,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Dependency that provides a database session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """Get a new database session (for non-generator use)."""
    SessionLocal = get_session_factory()
    return SessionLocal()


def init_db() -> None:
    """Initialize database tables."""
    from app.repositories.sqlalchemy import orm_models  # noqa: F401

    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def init_db_with_path(db_path: Path) -> None:
    """Initialize database at a specific path."""
    global _engine, _SessionLocal

    # Create database URL from path
    database_url = f"sqlite:///{db_path}"

    # Create new engine
    _engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create new session factory
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine,
    )

    # Import ORM models and create tables
    from app.repositories.sqlalchemy import orm_models  # noqa: F401
    Base.metadata.create_all(bind=_engine)


def reset_database() -> None:
    """Reset database state (for reconfiguration)."""
    global _engine, _SessionLocal

    if _engine is not None:
        _engine.dispose()

    _engine = None
    _SessionLocal = None


# Legacy compatibility: SessionLocal as property
@property
def SessionLocal():
    """Legacy accessor for session factory."""
    return get_session_factory()
