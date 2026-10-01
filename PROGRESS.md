# PROGRESS.md — ActionDesk Layer 1 Ingestion

## Step 1: Harness & Fixtures
- **Status**: COMPLETED
- **What was done**: Created `.gitignore` (secrets exclusions first), `config.yaml`, comprehensive test fixtures across Gmail, Drive, and QuickBooks including edge cases (empty responses, attachments, exclusions, errors).
- **Verify result**: `ruff`, `mypy`, `pytest` clean.

## Step 2: Unified Schema & SQLite Store
- **Status**: COMPLETED
- **What was done**:
  - `actiondesk/schema.py`: Defined `RawItem` Pydantic model with strict validations (UTC timezone, non-empty IDs, source literal), `make_id` deterministic ID generator, and SHA-256 `content_hash`.
  - `actiondesk/store.py`: Thread-safe SQLite store with WAL mode, unique constraint on `(source, source_item_id)`, idempotent upsert logic (updating only on content change), latest date watermark lookup, and transaction safety.
- **Verify result**: 18 unit tests passed (`test_schema.py`, `test_store.py`).

## Step 3: Read-Only Connectors
- **Status**: COMPLETED
- **What was done**:
  - `connectors/base.py`: Abstract base connector interface with date watermark support.
  - `connectors/gmail_connector.py`: Read-only connector enforcing `gmail.readonly` scope, label exclusion filtering, and conversion to `RawItem`.
  - `connectors/drive_connector.py`: Read-only connector enforcing `drive.readonly` scope, path/trashed exclusion filtering, and conversion to `RawItem`.
  - `connectors/quickbooks_connector.py`: Wrapped QuickBooks client in `ReadOnlyQuickBooksClient` that explicitly permits `GET` and query methods while raising `ReadOnlyViolationError` on `POST`, `PUT`, `PATCH`, `DELETE`.
- **Verify result**: 19 unit tests passed (`test_gmail.py`, `test_drive.py`, `test_quickbooks.py`).

## Step 4: Sync Engine & CLI
- **Status**: COMPLETED
- **What was done**:
  - `actiondesk/sync.py`: Incremental sync engine supporting `dry_run` mode, per-source watermark filtering, failure isolation, and atomic persistence of `status.json`.
  - `actiondesk/logging_config.py`: Structured JSON logger with ISO timestamps, log level, and secret redaction.
  - `actiondesk/status.py`: Formatted sync status table CLI with Windows terminal encoding compatibility.
- **Verify result**: 13 unit tests passed (`test_sync.py`), CLI dry-run and status verified.

## Step 5: Verification & Gate
- **Status**: COMPLETED
- **Checks**:
  - **Linter (Ruff)**: Clean (`All checks passed!`).
  - **Type Checker (Mypy)**: Clean (`Success: no issues found in 12 source files`, strict mode, zero errors).
  - **Test Suite (Pytest)**: 50 passed in 1.42s (100% pass rate).
  - **Dry-run Execution**: Verified against fixtures.
  - **Status CLI**: Verified table rendering.
