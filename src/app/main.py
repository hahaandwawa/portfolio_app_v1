"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config.settings import get_settings
from app.config.logging_config import setup_logging
from app.repositories.sqlalchemy.database import init_db
from app.api.routers import accounts_router, transactions_router, analysis_router
from app.core.exceptions import AppError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    setup_logging()
    init_db()
    yield
    # Shutdown (nothing to clean up)


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Local-first investment tracking and portfolio management",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(accounts_router)
app.include_router(transactions_router)
app.include_router(analysis_router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Global handler for application errors."""
    return JSONResponse(
        status_code=400,
        content={"error": exc.code, "message": exc.message},
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
def root() -> dict[str, str]:
    """Root endpoint with API info."""
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
