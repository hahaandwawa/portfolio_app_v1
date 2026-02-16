# Packaging Design Doc: Portfolio App → macOS .dmg (Real Desktop App)

## 0. Goal

Ship the Portfolio App as a real macOS desktop application that users install via .dmg and open by double-clicking an app icon.  
Users must NOT run servers, open terminals, or manually visit localhost.

User flow:
1. Download Portfolio App.dmg  
2. Drag Portfolio App.app into Applications  
3. Double-click Portfolio App  
4. App window opens and works immediately  

Behind the scenes:
- Electron opens a native window  
- Python backend runs invisibly  
- React UI loads inside the app window  
- All data persists locally  

This document defines a production-ready embedding architecture.

------------------------------------------------------------

## 1. High-Level Architecture

The packaged app contains:

Electron shell  
→ provides macOS app window  
→ launches backend process  
→ loads React UI  

FastAPI backend (bundled with PyInstaller)  
→ runs locally  
→ serves API  
→ stores SQLite data locally  

React frontend (built static files)  
→ loaded from disk inside Electron  
→ talks to backend via localhost  

Data storage  
→ SQLite files stored in user-writable directory  
→ NOT inside app bundle  

------------------------------------------------------------

## 2. Runtime Behavior

When user launches the app:

1. Electron starts  
2. Electron determines a writable user data directory  
3. Electron picks an available localhost port  
4. Electron launches bundled Python backend executable  
5. Backend starts FastAPI server on that port  
6. Electron polls /health until backend ready  
7. Electron opens window and loads React UI  
8. React UI communicates with backend via localhost  
9. On quit, Electron terminates backend process  

User never sees localhost or terminal.

------------------------------------------------------------

## 3. File System Design

IMPORTANT: App bundle is read-only.  
Never store SQLite databases inside the .app.

Use per-user writable directory:

~/Library/Application Support/Portfolio App/

Electron provides this path via:
app.getPath("userData")

Backend receives:
APP_DATA_DIR environment variable

Database locations:

APP_DATA_DIR/data/accounts.sqlite  
APP_DATA_DIR/data/transactions.sqlite  
APP_DATA_DIR/data/historical_prices.sqlite  

On first run:
- create directory if missing  
- create tables if missing  

------------------------------------------------------------

## 4. Repository Structure

Recommended structure:

portfolio_app/
  frontend/
    src/
    dist/                ← built React files
  backend/
    src/app/             ← existing FastAPI code
    entrypoint.py        ← NEW runtime launcher
    build.spec           ← PyInstaller spec
    requirements.txt
  electron/
    main.js
    preload.js
    package.json
    resources/
      frontend/          ← built UI copied here
      backend/           ← bundled backend binary
  scripts/
    build_macos.sh
  dist/                  ← final dmg output

------------------------------------------------------------

## 5. Backend Modifications

### 5.1 Add backend entrypoint

Create backend/entrypoint.py

Purpose:
Run uvicorn programmatically so PyInstaller can package it.

Contents:

import os  
import uvicorn  

def main():  
    port = int(os.environ.get("BACKEND_PORT", "8001"))  
    uvicorn.run("src.app.main:app", host="127.0.0.1", port=port)  

if __name__ == "__main__":
    main()  

------------------------------------------------------------

### 5.2 Use APP_DATA_DIR for SQLite paths

Backend must read APP_DATA_DIR env var.

If not provided (dev mode), fallback to local project directory.

Pseudo-logic:

APP_DATA_DIR = os.environ.get("APP_DATA_DIR")  
if not APP_DATA_DIR:  
    APP_DATA_DIR = os.path.abspath(".")  

DATA_DIR = os.path.join(APP_DATA_DIR, "data")  
os.makedirs(DATA_DIR, exist_ok=True)  

accounts_db = os.path.join(DATA_DIR, "accounts.sqlite")  
transactions_db = os.path.join(DATA_DIR, "transactions.sqlite")  
prices_db = os.path.join(DATA_DIR, "historical_prices.sqlite")  

Create tables if they do not exist.

------------------------------------------------------------

### 5.3 Health Endpoint

Backend must expose:

GET /health  
Returns status OK quickly

Used by Electron to detect readiness.

------------------------------------------------------------

## 6. Frontend Changes

### 6.1 Build React for production

Vite must build static files:

frontend/vite.config.ts should include:

base: './'  
build.outDir: 'dist'  

------------------------------------------------------------

### 6.2 Dynamic backend URL

Electron injects runtime backend URL into window.

Frontend API client must read:

window.BACKEND_URL

Fallback for dev mode remains /api.

Pseudo-logic:

const API_BASE_URL =  
  window.BACKEND_URL ||  
  (import.meta.env.DEV ? "/api" : "http://127.0.0.1:8001")

------------------------------------------------------------

## 7. Electron Responsibilities

Electron main process must:

- determine user data directory  
- choose free localhost port  
- spawn backend executable  
- pass env variables:  
    APP_DATA_DIR  
    BACKEND_PORT  
- poll /health until ready  
- load React UI from disk  
- send backend URL to renderer  
- kill backend on quit  

------------------------------------------------------------

## 8. Electron Main Process Logic

Steps:

1. On app ready:  
   userDataDir = app.getPath("userData")

2. Find free port:  
   open temporary socket  
   read assigned port  
   close socket  

3. backendUrl = http://127.0.0.1:PORT  

4. Launch backend executable:  
   spawn backend binary  
   pass env:  
     APP_DATA_DIR=userDataDir  
     BACKEND_PORT=PORT  

5. Poll backendUrl/health until success  

6. Create BrowserWindow  

7. Load React index.html from resources  

8. Send backendUrl to renderer  

9. On quit:  
   kill backend process  

------------------------------------------------------------

## 9. PyInstaller Build

### 9.1 build.spec

Entry script: entrypoint.py

Include hidden imports:  
uvicorn  
fastapi  
yfinance  
httpx  

Output:  
backend executable binary  

------------------------------------------------------------

### 9.2 Build command

cd backend  
pyinstaller build.spec  

Result:  
backend/dist/backend/backend (or similar)

Copy this binary into:

electron/resources/backend/backend

------------------------------------------------------------

## 10. Packaging Resources

Inside Electron packaged app:

resources/
  frontend/
    index.html
    assets/
  backend/
    backend   ← executable

Electron loads:

process.resourcesPath/frontend/index.html  
process.resourcesPath/backend/backend  

------------------------------------------------------------

## 11. Build Pipeline

Create scripts/build_macos.sh

Steps:

1. Build frontend  
cd frontend  
npm install  
npm run build  

2. Build backend  
cd ../backend  
pip install -r requirements.txt  
pyinstaller build.spec  

3. Assemble resources  
rm -rf electron/resources  
mkdir -p electron/resources/frontend  
mkdir -p electron/resources/backend  

cp -R frontend/dist/* electron/resources/frontend/  
cp backend/dist/backend/backend electron/resources/backend/backend  

4. Build dmg  
cd ../electron  
npm install  
npm run dist  

Output:  
electron/dist/Portfolio App.dmg

------------------------------------------------------------

## 12. Testing Plan

### Local test
- build dmg  
- install app  
- launch app  
- verify:  
  window opens  
  backend auto-starts  
  transactions save  
  data persists after restart  

### Clean machine test
- new macOS user or machine  
- install dmg  
- verify no Python/Node required  

### Data test
Check:  
~/Library/Application Support/Portfolio App/data/

SQLite files should appear there.

------------------------------------------------------------

## 13. macOS Distribution Notes

Unsigned apps may be blocked by Gatekeeper.

For public distribution:  
- sign app with Apple Developer ID  
- notarize build  

Not required for internal testing.

------------------------------------------------------------

## 14. Final Deliverables Checklist

Backend (implemented)  
- supports APP_DATA_DIR (via `src.service.util.get_data_dir` and `_load_config`)  
- supports BACKEND_PORT (via `entrypoint.py`)  
- exposes /health  
- initializes DB if missing  

Frontend (implemented)  
- production build works from disk (`base: "./"`, `build.outDir: "dist"` in vite.config)  
- reads backend URL dynamically (`window.BACKEND_URL` in `frontend/src/api/client.ts`)  

Electron  
- launches backend  
- waits for readiness  
- loads UI  
- kills backend on quit  

Packaging  
- PyInstaller builds backend binary  
- Electron bundles frontend + backend  
- build script produces dmg  

------------------------------------------------------------

## 15. Final Result

This architecture produces a real macOS app that:  
- installs via .dmg  
- opens like a native application  
- runs entirely locally  
- requires no manual setup  
- stores user data safely  
- hides all localhost/server complexity from the user