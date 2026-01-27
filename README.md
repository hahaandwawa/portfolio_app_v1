# Local Investment Management App (v1)

A local-first investment tracking application for managing portfolios, recording transactions, and computing simple analytics.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Layer                           │
│                  (routers, schemas, deps)                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                       Service Layer                             │
│  LedgerService │ PortfolioEngine │ MarketDataService │ Analysis │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                    Repository Protocols                         │
│         (AccountRepo │ TransactionRepo │ CacheRepo)             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                SQLAlchemy Implementations                       │
│                        (SQLite)                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

- **Local-first**: All data stored in SQLite; works offline
- **Ledger = Source of Truth**: Transaction history is authoritative
- **Derived Caches**: PositionCache/CashCache rebuilt from ledger (never edited directly)
- **Clean Architecture**: Domain layer has no dependencies on FastAPI or DB implementation

## Quick Start

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the app
uvicorn app.main:app --reload

# Run tests
pytest
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/accounts/` | Create account |
| GET | `/accounts/` | List accounts |
| GET | `/accounts/{id}` | Get account |
| POST | `/transactions/` | Add transaction |
| GET | `/transactions/` | Query transactions |
| PATCH | `/transactions/{id}` | Edit transaction |
| DELETE | `/transactions/{id}` | Soft delete transaction |
| POST | `/transactions/undo/{account_id}` | Undo last action |
| POST | `/transactions/import` | Import CSV |
| GET | `/transactions/export` | Export CSV |
| GET | `/analysis/positions` | Get holdings |
| GET | `/analysis/pnl` | Today's P/L |
| GET | `/analysis/allocation` | Allocation breakdown |

## Data Model

- **Account**: Top-level container with cost basis method config
- **Transaction**: Ledger entries (BUY/SELL/CASH_DEPOSIT/CASH_WITHDRAW)
- **TransactionRevision**: Audit trail for edits/deletes/restores
- **PositionCache**: Derived holdings per account (rebuilt from ledger)
- **CashCache**: Derived cash balance per account (rebuilt from ledger)

## Configuration

Environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_URL | sqlite:///./investment.db | SQLite connection string |
| ENFORCE_CASH_BALANCE | false | Reject withdrawals exceeding balance |
| LOG_LEVEL | INFO | Logging level |
