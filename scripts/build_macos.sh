#!/usr/bin/env bash
# Build Portfolio App for macOS: frontend, backend binary, Electron shell, then .dmg.
# Run from repo root. Requires: Node, npm, Python 3, pip, pyinstaller.

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Building frontend..."
cd frontend
npm install
npm run build
cd "$ROOT"

echo "==> Building backend (PyInstaller)..."
pip install -r requirements.txt
pip install pyinstaller
pyinstaller build.spec
cd "$ROOT"

echo "==> Assembling Electron resources..."
rm -rf electron/resources
mkdir -p electron/resources/frontend
mkdir -p electron/resources/backend

cp -R frontend/dist/* electron/resources/frontend/
cp dist/backend electron/resources/backend/backend
chmod +x electron/resources/backend/backend

echo "==> Building Electron app and DMG..."
cd electron
npm install
npm run dist
cd "$ROOT"

DMG_PATH=""
for f in electron/dist/"Portfolio App"*.dmg; do
  [[ -f "$f" ]] && DMG_PATH="$f" && break
done
if [[ -n "$DMG_PATH" ]]; then
  echo "==> Done. DMG: $DMG_PATH"
else
  echo "==> No DMG found in electron/dist/"
  exit 1
fi
