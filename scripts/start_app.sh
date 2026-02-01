#!/bin/bash
# Start both backend and frontend for 投资记录
# Press Ctrl+C to stop both
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Kill any existing backend on port 8001
if lsof -ti:8001 >/dev/null 2>&1; then
  echo "Stopping existing backend on port 8001..."
  lsof -ti:8001 | xargs kill -9 2>/dev/null
  sleep 1
fi

# Start backend in background
echo "Starting backend on http://127.0.0.1:8001..."
PYTHONPATH=. ./venv/bin/uvicorn src.app.main:app --host 127.0.0.1 --port 8001 &
BACKEND_PID=$!

# Ensure backend is killed when this script exits
cleanup() {
  echo ""
  echo "Stopping backend (PID $BACKEND_PID)..."
  kill $BACKEND_PID 2>/dev/null
  exit 0
}
trap cleanup SIGINT SIGTERM

# Wait for backend to be ready
BACKEND_READY=0
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if curl -s http://127.0.0.1:8001/ >/dev/null 2>&1; then
    echo "Backend ready."
    BACKEND_READY=1
    break
  fi
  if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "Backend failed to start."
    exit 1
  fi
  sleep 1
done
if [ "$BACKEND_READY" -eq 0 ]; then
  echo "Backend did not become ready in time."
  kill $BACKEND_PID 2>/dev/null
  exit 1
fi

# Start frontend (runs in foreground)
echo "Starting frontend on http://localhost:5173..."
cd frontend && npm run dev
