# Architecture Overview & Path to Local .dmg App

## Current Architecture (Inspection Summary)

### Stack

| Layer | Technology | Notes |
|-------|------------|--------|
| **Entry** | `uvicorn app.main:app` | ASGI server; app is HTTP API only |
| **API** | FastAPI | Routers: accounts, transactions, analysis |
| **Services** | LedgerService, PortfolioEngine, MarketDataService, AnalysisService | Business logic |
| **Repositories** | SQLAlchemy (protocols + implementations) | Account, Transaction, Cache |
| **Database** | SQLite | Single file; path from `DATABASE_URL` (default `./investment.db`) |
| **Config** | pydantic-settings | `.env` / env vars; `database_url`, `enforce_cash_balance`, `log_level` |
| **Market data** | StubMarketDataProvider | Offline stub; no external API required |

### Data Flow

- **Source of truth**: Ledger (transactions). Caches (positions, cash) are derived and rebuilt from the ledger.
- **Persistence**: One SQLite file. Path is global via `Settings.database_url` (no per-user or user-chosen directory yet).
- **No cloud**: No auth, no remote DB, no required external services. Already local-first.

### Gaps for “Fully Local App in User-Selected Directory”

1. **Data location**: App uses a fixed default path (`./investment.db`). You need to support a **user-selected data directory** and put the DB (and any future files) under that directory.
2. **Packaging**: Today the user runs `uvicorn` from a terminal. For a .dmg install, you need a **single installable app** (e.g. .app bundle) that runs the server and optionally a UI.
3. **UI**: The app is API-only (plus `/docs`). We will add a **local desktop UI** (Tkinter + ttk + matplotlib), not a web-based frontend.

---

## Can We Do This? Yes.

A fully local app that:

- Installs via a **.dmg** (or .pkg) on macOS,
- Stores **all data in a user-selected directory** on the user’s machine,

is achievable with your current design. Below is a concise path.

---

## 1. User-Selected Data Directory

**Goal**: All persistent data (DB, exports, logs, etc.) lives under one user-chosen folder (e.g. `~/Documents/Investment App Data`).

**Changes**:

- **Settings**: Add something like `data_dir: Path` (or keep `database_url` but derive it from `data_dir`, e.g. `data_dir / "investment.db"`). Allow override via env or config file.
- **First run**: If no `data_dir` is set, show a path selector (in your future UI) or use a sensible default (e.g. `~/Documents/Investment App Data` or app support path) and optionally let the user change it in “Preferences”.
- **Database**: Use `database_url = f"sqlite:///{data_dir / 'investment.db'}"` (with proper path handling for SQLite).
- **Other files**: Put CSV export, logs, and any future assets under `data_dir` so everything stays in one place and is easy to back up.

Your existing `Settings` + `database_url` in `database.py` already support a custom path; you only need to introduce `data_dir` and point `database_url` at it.

---

## 2. Local Desktop UI: Tkinter + ttk + matplotlib

**Goal**: A fully local, non–web-based app. No browser, no React/Electron/Tauri.

**UI stack**:

- **Tkinter** — Window management, menus, dialogs (e.g. data-directory picker, file open/save).
- **ttk** — Themed widgets (buttons, labels, entries, treeviews, notebooks) for a consistent native look.
- **matplotlib** — Charts and plots (allocation pie, P/L over time, etc.) embedded in Tk via `matplotlib.backends.backend_tkagg`.

The desktop app can either:

- **Call the backend in-process**: Import and use your services (LedgerService, AnalysisService, etc.) directly from the UI process, with no HTTP server. One process, one .app.
- **Or run the API locally**: Start uvicorn in a background thread/process and have the UI call `http://127.0.0.1:...` if you prefer to keep the API as the only entry point.

For a single-user local app, in-process usage is simpler and avoids running a server; the FastAPI layer can remain for testing or optional local API use.

---

## 3. Packaging as a macOS App (.dmg)

**Goal**: User downloads a .dmg, drags the app to Applications, and runs it without touching the terminal or Python.

**Approach**: Bundle the app (Python + Tkinter/ttk/matplotlib + your backend code) into a single macOS .app using [PyInstaller](https://pyinstaller.org/) (or similar). Tkinter and matplotlib are pure Python / stdlib-friendly, so they package well. The .app launches the Tkinter UI; no browser or web stack is involved.

**.dmg**: The .dmg is a disk image used to distribute the .app (e.g. drag-to-Applications). Create it with macOS tools (e.g. `hdiutil`) or CI (e.g. GitHub Actions) once you have the .app.

---

## 4. Recommended Order

1. **Introduce `data_dir`** in config and wire `database_url` (and any other paths) to it. Keep default or prompt on first run from the desktop UI.
2. **Keep the FastAPI backend as-is**; it already fits a local-only, single-user model.
3. **Add the local desktop UI** with Tkinter + ttk + matplotlib (accounts, transactions, analysis views, allocation/P/L charts). Either call services in-process or talk to the local API.
4. **Package**: Build the app (UI + backend) into a single .app with PyInstaller; then ship that .app inside a .dmg.

---

## Summary

| Question | Answer |
|----------|--------|
| Can we make it a fully local app? | **Yes.** Your stack is already local (SQLite, stub provider, no cloud). |
| Can we store everything in a user-selected directory? | **Yes.** Add a `data_dir` (or equivalent) and point the DB and other files there. |
| Can we distribute via .dmg? | **Yes.** Package the backend (and UI) as a macOS .app, then put the .app in a .dmg. |

The main follow-ups are: (1) implement `data_dir` and wire it through config and DB init, and (2) build the local desktop UI with Tkinter + ttk + matplotlib, then package as a .app and .dmg.
