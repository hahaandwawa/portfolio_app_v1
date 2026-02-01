#!/usr/bin/env bash
# Run all tests under src/tests. Use project venv.
set -e
cd "$(dirname "$0")/.."
if [[ ! -d venv ]]; then
  echo "Create venv first: python -m venv venv && ./venv/bin/pip install pytest"
  exit 1
fi
export PYTHONPATH="$PWD"
./venv/bin/pytest src/tests/ -v --tb=short "$@"
