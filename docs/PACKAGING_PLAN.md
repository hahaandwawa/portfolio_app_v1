# Packaging Plan: Portfolio App → macOS .dmg Installer

## Overview

This document outlines strategies for packaging your FastAPI + React portfolio management application into a distributable macOS application (.dmg file).

## Current Project Implementation

### Project Overview

This is a **full-stack portfolio management application** (投资记录) designed for tracking investment transactions, managing multiple accounts, and visualizing portfolio performance over time. The application provides a comprehensive solution for personal investment tracking with features like transaction management, portfolio overview, and historical net value curve visualization.

### Technology Stack

#### Backend Stack

**Core Framework:**
- **FastAPI** (v0.115.0+) - Modern, fast Python web framework for building APIs
- **Uvicorn** (v0.32.0+) - ASGI server for running FastAPI applications
- **Python 3.x** - Programming language

**Key Libraries:**
- **yfinance** (v0.2.40+) - Yahoo Finance API wrapper for fetching historical stock prices
- **httpx** (v0.27.0+) - HTTP client library for making API requests
- **python-multipart** (v0.0.9+) - For handling file uploads (CSV import)

**Database:**
- **SQLite3** - Lightweight, file-based relational database
  - `accounts.sqlite` - Stores account information
  - `transactions.sqlite` - Stores all transaction records
  - `historical_prices.sqlite` - Caches historical stock prices

**Architecture Pattern:**
- **Service Layer Architecture** - Business logic separated into service classes
- **Repository Pattern** - Database access abstracted through service layer
- **RESTful API** - Standard HTTP methods (GET, POST, PUT, DELETE)

#### Frontend Stack

**Core Framework:**
- **React 19** - Modern UI library for building user interfaces
- **TypeScript** (~5.9.3) - Type-safe JavaScript superset
- **Vite** (v7.2.4+) - Fast build tool and dev server

**UI Libraries:**
- **Tailwind CSS v4** - Utility-first CSS framework for styling
- **Recharts** (v3.7.0) - React charting library for data visualization

**Development Tools:**
- **ESLint** - Code linting and quality checks
- **Vitest** - Unit testing framework
- **TypeScript ESLint** - TypeScript-specific linting rules

**Architecture Pattern:**
- **Component-Based Architecture** - Modular, reusable React components
- **Hooks-Based State Management** - React hooks for state and side effects
- **API Client Abstraction** - Centralized API communication layer

---

### System Architecture

#### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                     │
│  ┌───────────────────────────────────────────────────────┐ │
│  │         React Frontend (Port 5173)                    │ │
│  │  - TopBar (Account Filter, Add Transaction)          │ │
│  │  - GeneralOverviewBlock                              │ │
│  │  - AccountManagementBlock                            │ │
│  │  - PortfolioBlock (Positions Table)                  │ │
│  │  - NetValueCurve (Historical Performance Chart)      │ │
│  │  - TransactionBlock (Transaction Table)              │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↕ HTTP/REST API
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (FastAPI)                      │
│  ┌───────────────────────────────────────────────────────┐ │
│  │         FastAPI Backend (Port 8001)                  │ │
│  │  - CORS Middleware                                    │ │
│  │  - API Routers:                                       │ │
│  │    • /accounts                                        │ │
│  │    • /transactions                                    │ │
│  │    • /portfolio                                       │ │
│  │    • /net-value-curve                                 │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↕ Service Layer
┌─────────────────────────────────────────────────────────────┐
│                  Business Logic Layer                        │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Service Classes:                                     │ │
│  │  - AccountService                                     │ │
│  │  - TransactionService                                 │ │
│  │  - PortfolioService                                   │ │
│  │  - NetValueService                                    │ │
│  │  - HistoricalPriceService                             │ │
│  │  - QuoteService                                       │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↕ Data Access
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  SQLite Databases:                                    │ │
│  │  - accounts.sqlite                                   │ │
│  │  - transactions.sqlite                               │ │
│  │  - historical_prices.sqlite                           │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                          ↕ External API
┌─────────────────────────────────────────────────────────────┐
│              External Services                               │
│  ┌───────────────────────────────────────────────────────┐ │
│  │  Yahoo Finance API (via yfinance)                     │ │
│  │  - Historical stock prices                            │ │
│  │  - Real-time quotes                                   │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

#### Backend Architecture Details

**1. API Router Structure**

The backend is organized into four main API routers:

- **`/accounts`** - Account CRUD operations
  - `GET /accounts` - List all accounts
  - `POST /accounts` - Create new account
  - `PUT /accounts/{name}` - Rename account
  - `DELETE /accounts/{name}` - Delete account

- **`/transactions`** - Transaction management
  - `GET /transactions` - List transactions (with pagination and filtering)
  - `POST /transactions` - Create new transaction
  - `PUT /transactions/{txn_id}` - Update transaction
  - `DELETE /transactions/{txn_id}` - Delete transaction
  - `POST /transactions/import` - Bulk import from CSV
  - `GET /transactions/export` - Export transactions as CSV
  - `GET /transactions/template` - Download CSV template

- **`/portfolio`** - Portfolio summary and positions
  - `GET /portfolio` - Get portfolio summary (positions + cash)
  - `GET /portfolio/positions-by-symbol` - Get positions for a symbol across accounts

- **`/net-value-curve`** - Historical performance visualization
  - `GET /net-value-curve` - Get baseline and market value over time
  - Parameters: `account`, `start_date`, `end_date`, `include_cash`, `refresh`

**2. Service Layer**

The business logic is encapsulated in service classes:

- **`AccountService`** - Manages account operations and validation
- **`TransactionService`** - Handles transaction CRUD, validation, and business rules
- **`PortfolioService`** - Calculates portfolio positions, cash balances, and holdings
- **`NetValueService`** - Computes historical net value curve (baseline vs market value)
- **`HistoricalPriceService`** - Fetches and caches stock prices from Yahoo Finance
- **`QuoteService`** - Provides real-time stock quotes

**3. Database Schema**

**Accounts Table:**
```sql
CREATE TABLE accounts (
    name TEXT NOT NULL PRIMARY KEY
)
```

**Transactions Table:**
```sql
CREATE TABLE transactions (
    txn_id TEXT NOT NULL PRIMARY KEY,
    account_name TEXT NOT NULL,
    txn_type TEXT NOT NULL,  -- BUY, SELL, CASH_DEPOSIT, CASH_WITHDRAW
    txn_time_est TEXT NOT NULL,
    symbol TEXT,
    quantity REAL,
    price REAL,
    cash_amount REAL,
    fees REAL,
    note TEXT,
    cash_destination_account TEXT
)
```

**Historical Prices Table:**
```sql
CREATE TABLE historical_prices (
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    close_price REAL NOT NULL,
    adj_close_price REAL,
    price_type TEXT NOT NULL DEFAULT 'close',
    updated_at TEXT NOT NULL,
    PRIMARY KEY (symbol, date)
)
CREATE INDEX idx_historical_prices_symbol_date ON historical_prices(symbol, date)
```

**4. Key Algorithms**

**Average Cost Calculation (Weighted Average):**
- On BUY: `avg_cost = (prev_shares × prev_avg_cost + buy_qty × buy_price + fees) / (prev_shares + buy_qty)`
- On SELL: `avg_cost` remains unchanged (only shares decrease)
- When shares = 0: `avg_cost` resets to 0

**Net Value Curve Computation:**
- Day-by-day incremental calculation from transaction history
- Baseline = Holdings Cost (avg_cost × shares) + Cash (if included)
- Market Value = Current Price × Shares + Cash (if included)
- Forward-fills non-trading days with previous trading day's close price

#### Frontend Architecture Details

**1. Component Structure**

The frontend follows a component-based architecture:

```
frontend/src/
├── components/
│   ├── TopBar/
│   │   ├── TopBar.tsx                    # Main navigation bar
│   │   ├── AccountFilterDropdown.tsx     # Account selection
│   │   ├── AddTransactionModal.tsx       # Transaction form
│   │   ├── CsvModal.tsx                  # CSV import/export
│   │   └── ThemeToggle.tsx               # Dark/light mode
│   ├── GeneralOverviewBlock/
│   │   └── GeneralOverviewBlock.tsx      # Portfolio summary cards
│   ├── AccountManagementBlock/
│   │   ├── AccountManagementBlock.tsx
│   │   ├── AddAccountModal.tsx
│   │   ├── EditAccountModal.tsx
│   │   └── AccountListItem.tsx
│   ├── PortfolioBlock/
│   │   ├── PortfolioBlock.tsx
│   │   └── PortfolioTable.tsx             # Positions table
│   ├── NetValueCurve/
│   │   └── NetValueCurve.tsx              # Historical chart
│   ├── TransactionBlock/
│   │   ├── TransactionBlock.tsx
│   │   ├── TransactionTable.tsx           # Transaction list
│   │   ├── EditTransactionModal.tsx
│   │   └── Pagination.tsx
│   ├── Modal.tsx                          # Base modal component
│   └── ConfirmModal.tsx                   # Confirmation dialog
├── api/
│   └── client.ts                          # API client abstraction
├── types/
│   └── index.ts                           # TypeScript type definitions
├── App.tsx                                # Main app component
└── main.tsx                              # Entry point
```

**2. State Management**

The application uses React hooks for state management:

- **`useState`** - Local component state
- **`useEffect`** - Side effects and data fetching
- **`useCallback`** - Memoized callback functions
- **`useMemo`** - Computed values caching

**State Flow:**
```
App Component (Root State)
├── accounts: Account[]
├── selectedAccountNames: Set<string>
├── portfolio: PortfolioSummary | null
├── netValueCurve: NetValueCurveResponse | null
└── refreshKey: number (for forcing re-fetches)
```

**3. API Communication**

The frontend uses a centralized API client (`api/client.ts`) that:
- Abstracts HTTP requests
- Handles error parsing and formatting
- Provides type-safe methods for each endpoint
- Manages query parameter construction
- Handles file uploads/downloads (CSV)

**4. Data Visualization**

**Net Value Curve Chart:**
- Uses Recharts library for rendering
- Displays two lines: Baseline (gray dashed) and Market Value (blue solid)
- Color-coded fill areas: Green (profit) and Red (loss)
- Interactive tooltips showing detailed metrics
- Supports date range filtering (7 days, 30 days, All time)
- Toggle for including/excluding cash

---

### Data Flow Examples

#### Example 1: Adding a Transaction

```
1. User fills form in AddTransactionModal
   ↓
2. Frontend calls api.postTransaction(payload)
   ↓
3. POST /transactions → FastAPI router
   ↓
4. TransactionService.create_transaction()
   - Validates transaction data
   - Calculates average cost (if BUY)
   - Updates cash balance
   ↓
5. SQLite: INSERT INTO transactions
   ↓
6. Response returned to frontend
   ↓
7. App component refreshes (refreshKey++)
   ↓
8. useEffect triggers re-fetch of:
   - Portfolio summary
   - Net value curve
   - Transaction list
```

#### Example 2: Viewing Net Value Curve

```
1. User selects accounts and date range
   ↓
2. Frontend calls api.getNetValueCurve(params)
   ↓
3. GET /net-value-curve → FastAPI router
   ↓
4. NetValueService.get_net_value_curve()
   - Fetches all transactions for selected accounts
   - Groups transactions by date
   - Identifies symbols in date range
   ↓
5. HistoricalPriceService.get_historical_prices()
   - Checks SQLite cache for prices
   - Fetches missing prices from yfinance
   - Caches new prices
   - Forward-fills weekends/holidays
   ↓
6. Day-by-day calculation:
   - Apply transactions for each day
   - Calculate holdings (shares × avg_cost)
   - Calculate market value (shares × close_price)
   - Compute profit/loss
   ↓
7. Return columnar arrays (dates, baseline, market_value, etc.)
   ↓
8. Frontend renders chart using Recharts
```

---

### Key Features Implementation

**1. Multi-Account Support**
- Each transaction is associated with an account
- Portfolio calculations can filter by account(s)
- Net value curve supports multiple account selection
- Account-level cash balance tracking

**2. Transaction Types**
- **BUY**: Purchases stock, updates holdings and average cost
- **SELL**: Sells stock, reduces holdings (avg_cost unchanged)
- **CASH_DEPOSIT**: Adds cash to account
- **CASH_WITHDRAW**: Removes cash from account

**3. CSV Import/Export**
- Bulk transaction import from CSV file
- Export transactions to CSV
- Template download for correct format
- Validation and error reporting

**4. Historical Price Caching**
- SQLite cache prevents redundant API calls
- Forward-fills non-trading days
- Refresh option to force re-fetch
- Efficient batch fetching from Yahoo Finance

**5. Real-time Portfolio Updates**
- Automatic refresh on transaction changes
- Real-time stock price fetching (via QuoteService)
- Calculated metrics: P/L, P/L%, weight percentage

---

### Development Workflow

**Backend Development:**
```bash
# Start backend server
PYTHONPATH=. uvicorn src.app.main:app --host 127.0.0.1 --port 8001

# Or use helper script
./scripts/start_backend.sh
```

**Frontend Development:**
```bash
# Start Vite dev server
cd frontend && npm run dev

# Or use helper script
./scripts/start_frontend.sh
```

**Full Stack Development:**
```bash
# Start both backend and frontend
./scripts/start_app.sh
```

**Testing:**
```bash
# Backend tests
pytest src/tests/ -v

# Frontend tests
cd frontend && npm test
```

---

### Configuration

**Backend Configuration (`config.json`):**
```json
{
  "AccountDBPath": "./data/accounts.sqlite",
  "TransactionDBPath": "./data/transactions.sqlite",
  "HistoricalPricesDBPath": "./data/historical_prices.sqlite"
}
```

**Frontend Configuration (`vite.config.ts`):**
- Development proxy: `/api/*` → `http://127.0.0.1:8001/*`
- Production: Direct API calls to backend

**CORS Configuration:**
- Currently allows: `http://localhost:5173` and `http://127.0.0.1:5173`
- Will need update for Electron packaging

---

### Current Architecture

- **Backend**: FastAPI (Python) running on `127.0.0.1:8001`
- **Frontend**: React + Vite + TypeScript running on `localhost:5173`
- **Database**: SQLite files in `data/` directory
- **Dependencies**: Python (requirements.txt) + Node.js (frontend/package.json)

---

## Packaging Options

### Option 1: Electron + PyInstaller (Recommended) ⭐

**Architecture:**
- Electron wraps the React frontend as a native macOS app
- PyInstaller bundles the FastAPI backend into a standalone executable
- Both bundled together in a single .app bundle
- Electron Forge generates the .dmg installer

**Pros:**
- ✅ Most mature and well-documented approach
- ✅ Cross-platform (can build for Windows/Linux too)
- ✅ Rich ecosystem and community support
- ✅ Good performance for desktop apps
- ✅ Can use native macOS features (menus, notifications, etc.)

**Cons:**
- ❌ Larger bundle size (~100-150MB)
- ❌ Requires Electron dependency
- ❌ More complex setup initially

**Estimated Bundle Size:** ~120-150MB

**Implementation Complexity:** Medium-High

---

### Option 2: Tauri + PyTauri (Modern Alternative) 🚀

**Architecture:**
- Tauri wraps the React frontend (uses system WebView, not bundled browser)
- PyTauri embeds Python runtime directly into the app
- Smaller footprint than Electron
- Native macOS bundle generation

**Pros:**
- ✅ Much smaller bundle size (~20-40MB)
- ✅ Better performance (uses system WebView)
- ✅ Modern Rust-based architecture
- ✅ Better security model
- ✅ Native look and feel

**Cons:**
- ❌ Less mature ecosystem
- ❌ Requires Rust toolchain for building
- ❌ Fewer examples/templates available
- ❌ Learning curve for Rust configuration

**Estimated Bundle Size:** ~25-40MB

**Implementation Complexity:** Medium

---

### Option 3: PyInstaller Standalone + Embedded Web Server

**Architecture:**
- PyInstaller bundles FastAPI backend + embedded web server
- Frontend built as static files and embedded in Python bundle
- Single executable launches both backend and opens browser

**Pros:**
- ✅ Simplest approach (no Electron/Tauri)
- ✅ Smallest bundle size (~30-50MB)
- ✅ Single executable file
- ✅ No additional runtime dependencies

**Cons:**
- ❌ Less polished UI (opens in system browser)
- ❌ No native app feel
- ❌ Browser dependency (user must have browser installed)
- ❌ Less control over app lifecycle

**Estimated Bundle Size:** ~30-50MB

**Implementation Complexity:** Low-Medium

---

## Recommended Approach: Electron + PyInstaller

Given your current stack and the need for a polished desktop experience, **Option 1 (Electron + PyInstaller)** is recommended.

### Architecture Diagram

```
┌─────────────────────────────────────────┐
│         Portfolio App.app                │
│  ┌───────────────────────────────────┐  │
│  │      Electron Shell               │  │
│  │  ┌─────────────────────────────┐  │  │
│  │  │   React Frontend (Built)    │  │  │
│  │  │   (Static files from Vite)  │  │  │
│  │  └─────────────────────────────┘  │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │   FastAPI Backend (PyInstaller)  │  │
│  │   - Python runtime               │  │
│  │   - All dependencies             │  │
│  │   - SQLite databases             │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │   Data Directory                  │  │
│  │   - accounts.sqlite              │  │
│  │   - transactions.sqlite          │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: Preparation & Setup

#### 1.1 Modify Frontend for Production Build
- [ ] Update Vite config to build static files
- [ ] Configure API endpoint for production (no proxy)
- [ ] Test production build locally

#### 1.2 Modify Backend for Embedded Mode
- [ ] Update CORS to allow Electron origin
- [ ] Configure database paths for app bundle
- [ ] Add startup script to launch backend
- [ ] Test PyInstaller build locally

#### 1.3 Project Structure Changes
```
portfolio_app_v1/
├── electron/              # New Electron wrapper
│   ├── main.js           # Electron main process
│   ├── preload.js        # Preload script
│   └── package.json      # Electron dependencies
├── frontend/             # Existing React app
├── backend/              # New: Backend packaging
│   ├── build.py          # PyInstaller spec
│   └── requirements.txt  # Backend deps
├── build/                # Build output
└── dist/                 # Distribution files (.dmg)
```

---

### Phase 2: Electron Integration

#### 2.1 Create Electron Wrapper
- [ ] Initialize Electron project
- [ ] Create main process (main.js)
- [ ] Configure to load built React app
- [ ] Set up IPC communication
- [ ] Handle app lifecycle (quit, window close)

#### 2.2 Integrate Backend
- [ ] Spawn PyInstaller backend executable from Electron
- [ ] Wait for backend to be ready
- [ ] Handle backend process lifecycle
- [ ] Error handling for backend failures

#### 2.3 Frontend Integration
- [ ] Update API client to use localhost backend
- [ ] Remove Vite dev server dependency
- [ ] Test Electron app with embedded frontend

---

### Phase 3: Backend Packaging

#### 3.1 PyInstaller Configuration
- [ ] Create PyInstaller spec file
- [ ] Bundle all Python dependencies
- [ ] Include SQLite database files
- [ ] Configure hidden imports
- [ ] Test standalone executable

#### 3.2 Database Path Configuration
- [ ] Update database paths to use app bundle location
- [ ] Handle data directory creation
- [ ] Ensure data persistence across app updates

---

### Phase 4: Build & Distribution

#### 4.1 Build Scripts
- [ ] Create unified build script
- [ ] Build frontend (Vite)
- [ ] Build backend (PyInstaller)
- [ ] Package Electron app
- [ ] Generate .dmg file

#### 4.2 Electron Forge Configuration
- [ ] Configure Electron Forge
- [ ] Set up macOS-specific makers
- [ ] Configure app metadata (name, icon, etc.)
- [ ] Set up code signing (optional, for distribution)

#### 4.3 Testing
- [ ] Test on clean macOS system
- [ ] Verify all features work
- [ ] Test database persistence
- [ ] Performance testing

---

## Detailed Implementation Steps

### Step 1: Frontend Production Build

**File: `frontend/vite.config.ts`**
```typescript
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: './', // Important for Electron
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
  // Remove proxy in production
  server: {
    proxy: process.env.NODE_ENV === 'development' ? {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    } : undefined,
  },
})
```

**File: `frontend/src/api/client.ts`**
```typescript
// Update base URL for production
const API_BASE_URL = import.meta.env.PROD 
  ? 'http://127.0.0.1:8001'  // Electron backend
  : '/api';  // Dev proxy
```

---

### Step 2: Electron Setup

**Create `electron/package.json`:**
```json
{
  "name": "portfolio-app",
  "version": "1.0.0",
  "main": "main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder"
  },
  "devDependencies": {
    "electron": "^latest",
    "electron-builder": "^latest"
  }
}
```

**Create `electron/main.js`:**
```javascript
const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let backendProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  // Load built React app
  const isDev = process.env.NODE_ENV === 'development';
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'));
  }

  // Start backend
  startBackend();
}

function startBackend() {
  const backendPath = path.join(__dirname, '../backend/dist/backend');
  backendProcess = spawn(backendPath, [], {
    cwd: path.join(__dirname, '../backend/dist'),
  });

  backendProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`Backend error: ${data}`);
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});
```

---

### Step 3: PyInstaller Configuration

**Create `backend/build.spec`:**
```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['../src/app/main.py'],
    pathex=['../src'],
    binaries=[],
    datas=[
        ('../data', 'data'),  # Include database files
    ],
    hiddenimports=[
        'uvicorn',
        'fastapi',
        'yfinance',
        'httpx',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False to hide console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

**Build command:**
```bash
cd backend
pyinstaller build.spec
```

---

### Step 4: Electron Builder Configuration

**Update `electron/package.json`:**
```json
{
  "build": {
    "appId": "com.yourname.portfolio-app",
    "productName": "Portfolio App",
    "directories": {
      "output": "../../dist"
    },
    "mac": {
      "category": "public.app-category.finance",
      "target": [
        {
          "target": "dmg",
          "arch": ["x64", "arm64"]
        }
      ],
      "icon": "assets/icon.icns"
    },
    "files": [
      "../frontend/dist/**/*",
      "../backend/dist/**/*",
      "main.js"
    ]
  }
}
```

---

## Build Process

### Development Build
```bash
# 1. Build frontend
cd frontend && npm run build

# 2. Build backend
cd backend && pyinstaller build.spec

# 3. Run Electron
cd electron && npm start
```

### Production Build (.dmg)
```bash
# 1. Build frontend
cd frontend && npm run build

# 2. Build backend
cd backend && pyinstaller build.spec

# 3. Build Electron app and create .dmg
cd electron && npm run build
```

Output: `dist/Portfolio App-1.0.0.dmg`

---

## Alternative: Simplified Script-Based Approach

If Electron seems too complex, a simpler approach:

### Option: Shell Script Launcher

**Create `PortfolioApp.app/Contents/MacOS/PortfolioApp`:**
```bash
#!/bin/bash
# Launch backend
/path/to/backend/executable &
BACKEND_PID=$!

# Wait for backend
sleep 2

# Open frontend in browser
open http://127.0.0.1:8001

# Keep script running
wait $BACKEND_PID
```

**Pros:** Very simple, no Electron needed  
**Cons:** Opens in browser, less native feel

---

## Next Steps

1. **Choose approach** (recommended: Electron + PyInstaller)
2. **Set up development environment**
   - Install Electron CLI
   - Install PyInstaller
   - Install electron-builder
3. **Implement Phase 1** (frontend/backend modifications)
4. **Test locally** before packaging
5. **Create build scripts** for automation
6. **Generate .dmg** and test on clean system

---

## Resources

- [Electron Documentation](https://www.electronjs.org/docs)
- [Electron Builder](https://www.electron.build/)
- [PyInstaller Manual](https://pyinstaller.org/)
- [Electron + React + FastAPI Template](https://medium.com/@shakeef.rakin321/electron-react-fastapi-template-for-cross-platform-desktop-apps-cf31d56c470c)

---

## Questions to Consider

1. **Code Signing**: Do you want to sign the app for distribution? (Required for App Store, recommended for direct distribution)
2. **Auto-updates**: Do you want to implement auto-update functionality?
3. **Data Location**: Where should user data be stored? (`~/Library/Application Support/PortfolioApp/`)
4. **Multi-user**: Should each macOS user have separate data?
5. **Offline Mode**: Does the app need to work completely offline? (Yahoo Finance API requires internet)

---

## Estimated Timeline

- **Phase 1**: 2-3 days (setup and modifications)
- **Phase 2**: 3-4 days (Electron integration)
- **Phase 3**: 2-3 days (PyInstaller packaging)
- **Phase 4**: 2-3 days (build scripts and testing)

**Total**: ~2 weeks for complete implementation

---

## Conclusion

Yes, it's definitely possible! The Electron + PyInstaller approach is the most proven method for packaging FastAPI + React apps into macOS distributables. The resulting .dmg file will be a self-contained application that users can drag to Applications folder and run without any additional setup.
