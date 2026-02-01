#!/bin/bash
# Start the FastAPI backend for 投资记录
cd "$(dirname "$0")/.."
PYTHONPATH=. ./venv/bin/uvicorn src.app.main:app --host 127.0.0.1 --port 8001
