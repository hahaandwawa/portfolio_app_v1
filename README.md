# Local Investment Management App (v1)

A **fully local** investment tracking application with a native desktop UI. All data stays on your machine in a user-selected directory.

## Features

- **Local-first**: All data stored locally in SQLite; works completely offline
- **Native Desktop UI**: Built with Tkinter + ttk + matplotlib (no browser required)
- **User-selected data directory**: Choose where your data is stored
- **Multi-account support**: Track multiple investment accounts
- **Transaction ledger**: Record buys, sells, deposits, and withdrawals
- **Portfolio analytics**: Today's P/L, allocation breakdown, holdings overview
- **CSV import/export**: Bulk import transactions or export for backup

## Quick Start

### Running the Desktop App

```bash
# Install dependencies
pip install -e .

# Run the desktop app
python -m app.main_desktop

# Or use the installed command
investment-app
```

### Running the API Server (Optional)

The FastAPI server is still available for testing or programmatic access:

```bash
# Install API dependencies
pip install -e ".[api]"

# Run the API server
uvicorn app.main:app --reload

# API docs at: http://127.0.0.1:8000/docs
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Desktop UI (Tkinter + ttk)                   │
│         MainWindow │ AccountsView │ TransactionsView │          │
│                    │ AnalysisView (matplotlib charts)           │
└─────────────────────────────┬───────────────────────────────────┘
                              │ (in-process calls)
┌─────────────────────────────▼───────────────────────────────────┐
│                       AppContext                                │
│         (Service management for desktop UI)                     │
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

- **Local-first**: All data in SQLite; works offline
- **Ledger = Source of Truth**: Transaction history is authoritative
- **Derived Caches**: PositionCache/CashCache rebuilt from ledger
- **In-process services**: Desktop UI calls services directly (no HTTP)
- **Clean Architecture**: Domain layer has no dependencies on UI or DB

## Data Storage

All application data is stored in a user-selected directory (default: `~/Documents/Investment App Data`):

```
Investment App Data/
├── investment.db      # SQLite database
├── exports/           # CSV exports
└── logs/              # Application logs
```

You can change this directory in Preferences or on first run.

## Data Model

- **Account**: Investment account with cost basis method config
- **Transaction**: Ledger entries (BUY/SELL/CASH_DEPOSIT/CASH_WITHDRAW)
- **TransactionRevision**: Audit trail for edits/deletes/restores
- **PositionCache**: Derived holdings per account (rebuilt from ledger)
- **CashCache**: Derived cash balance per account (rebuilt from ledger)

## CSV Format

For importing transactions:

| Column | Description |
|--------|-------------|
| account_name | Account name (creates if doesn't exist) |
| txn_time_est | Date/time in US/Eastern (YYYY-MM-DD HH:MM) |
| type | BUY, SELL, CASH_DEPOSIT, or CASH_WITHDRAW |
| symbol | Stock symbol (for BUY/SELL) |
| quantity | Number of shares (for BUY/SELL) |
| price | Price per share (for BUY/SELL) |
| cash_amount | Cash amount (for deposits/withdrawals) |
| fees | Transaction fees |
| note | Optional note |

## Development

```bash
# Install all dependencies (including dev)
pip install -e ".[dev]"

# Run tests
pytest -v

# Run with coverage
pytest --cov=app tests/
```

## Packaging as .app / .dmg (macOS)

To create a standalone macOS application:

```bash
# Install PyInstaller
pip install pyinstaller

# Build the app
pyinstaller --name "Investment App" \
    --windowed \
    --onedir \
    --add-data "src/app:app" \
    src/app/main_desktop.py

# The .app will be in dist/Investment App.app
```

Then create a .dmg for distribution using macOS tools (`hdiutil`).

## Configuration

Environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| DATA_DIR | ~/Documents/Investment App Data | Data directory path |
| DATABASE_URL | (derived from DATA_DIR) | SQLite connection string |
| ENFORCE_CASH_BALANCE | false | Reject withdrawals exceeding balance |
| LOG_LEVEL | INFO | Logging level |
