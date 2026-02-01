#!/usr/bin/env python3
"""
Run all tests in src/tests.
Usage: from project root:
  ./venv/bin/python scripts/run_all_tests.py
  or: ./venv/bin/pytest src/tests/ -v
"""
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def main():
    pytest_exe = PROJECT_ROOT / "venv" / "bin" / "pytest"
    if not pytest_exe.exists():
        print("venv not found. Create it and install pytest: python -m venv venv && ./venv/bin/pip install pytest")
        sys.exit(1)
    tests_dir = PROJECT_ROOT / "src" / "tests"
    env = {**os.environ, "PYTHONPATH": str(PROJECT_ROOT)}
    cmd = [str(pytest_exe), str(tests_dir), "-v", "--tb=short"]
    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
