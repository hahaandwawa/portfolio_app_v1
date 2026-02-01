# Service tests

Tests for `AccountService` and `TransactionService` in `src/service/`.

## Layout

- **conftest.py** – Pytest fixtures: test cache dir, temp DB dirs, `accounts`/`transactions` schema, `AccountService`/`TransactionService` instances, and helpers (`make_transaction_create`, `account_for_transactions`).
- **test_account_service.py** – Tests for `AccountService`: init, save_account, validation, create_account, create_batch_account, get_account, edit_account, delete_account (common and edge cases).
- **test_transaction_service.py** – Tests for `TransactionService`: init, account validation, BUY/SELL and CASH_DEPOSIT/CASH_WITHDRAW validation, create/batch create, get_transaction, _row_to_transaction_create, edit_transaction, delete_transaction (common and edge cases).

Test DBs are created under `src/tests/.test_cache/` in temporary subdirs so each run is isolated.

## Run all tests

From project root, using the project venv:

```bash
# Option 1: pytest directly
export PYTHONPATH=.
./venv/bin/pytest src/tests/ -v --tb=short

# Option 2: run script (sets PYTHONPATH)
./venv/bin/python scripts/run_all_tests.py

# Option 3: shell script
chmod +x scripts/run_all_tests.sh
./scripts/run_all_tests.sh
```

Extra pytest args (e.g. `-k test_edit`, `--tb=long`) can be passed to the shell script: `./scripts/run_all_tests.sh -k test_edit`.
