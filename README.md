# ActionDesk — Layer 1 Ingestion

Read-only ingestion system for small business operations across Gmail, Google Drive, and QuickBooks into a standardized SQLite store.

## Architecture & Principles
1. **Strict Read-Only Access**:
   - Google APIs use read-only scopes (`gmail.readonly`, `drive.readonly`).
   - QuickBooks API client is wrapped in `ReadOnlyQuickBooksClient` that permits `GET` / queries and raises `ReadOnlyViolationError` on any mutation HTTP verbs (`POST`, `PUT`, `PATCH`, `DELETE`).
2. **Unified Data Model**: Every record from every source is normalized to a validated `RawItem` schema with deterministic content hashing and SHA-256 IDs.
3. **Idempotent & Incremental Sync**: Syncs record an ingestion timestamp watermark per source and store items with a `UNIQUE(source, source_item_id)` constraint, preventing duplicates.
4. **Failure Isolation**: An outage or exception in one connector does not disrupt syncing the remaining sources.
5. **Dry-Run Mode**: Inspect incoming data and schema validation without modifying SQLite.
6. **No Committed Secrets**: `.gitignore` strictly protects `.env`, tokens, and credentials.

---

## Setup & Quickstart (Under 10 Steps)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Aditya-coder-ai/Business-helper.git
   cd Business-helper
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # Windows PowerShell:
   .\venv\Scripts\Activate.ps1
   # macOS / Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify all tests, linter, and type checks**:
   ```bash
   # On systems with make:
   make verify
   # Or directly with Python:
   python -m ruff check actiondesk/ connectors/ tests/
   python -m mypy actiondesk/ connectors/ --ignore-missing-imports
   python -m pytest tests/ -v
   ```

5. **Run a dry-run sync against fixtures**:
   ```bash
   # Executes connectors in dry-run mode (writes 0 rows):
   make sync-dry
   ```

6. **Check sync status**:
   ```bash
   python -m actiondesk.status
   ```

7. **Configure exclusions & live sources (Optional)**:
   Review `config.yaml` to adjust sync intervals, history windows, or add privacy exclusion rules for specific Gmail labels or Drive folder IDs.

8. **Automated Layer 1 Agent (Optional)**:
   To run an autonomous build agent using Anthropic's Claude API against the harness:
   ```bash
   pip install anthropic
   export ANTHROPIC_API_KEY="your-api-key"
   python layer1_agent.py
   ```

---

## Project Structure
```text
.
├── actiondesk/
│   ├── config.py           # Configuration loader & exclusion parsing
│   ├── logging_config.py   # Structured JSON logger (no secrets)
│   ├── schema.py           # Pydantic RawItem model & hashing
│   ├── status.py           # CLI status table printer
│   ├── store.py            # SQLite WAL-mode store with unique constraints
│   └── sync.py             # Incremental sync orchestrator
├── connectors/
│   ├── base.py             # BaseConnector interface
│   ├── drive_connector.py  # Read-only Drive connector
│   ├── gmail_connector.py  # Read-only Gmail connector
│   └── quickbooks_connector.py # ReadOnlyQuickBooksClient guard & connector
├── tests/                  # 50 unit and integration tests with mocks
├── layer1_agent.py         # Autonomous Claude build agent
├── layer1_prompt.md        # System prompt for layer1_agent
├── Makefile                # Verification and operational targets
└── PROGRESS.md             # Ingestion progress and verify log
```
