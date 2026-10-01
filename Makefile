.PHONY: test lint typecheck verify sync-dry status clean

# Run all tests
test:
	python -m pytest tests/ -v --tb=short

# Lint with ruff
lint:
	python -m ruff check actiondesk/ connectors/ tests/

# Type check with mypy
typecheck:
	python -m mypy actiondesk/ connectors/ --ignore-missing-imports

# THE GATE — all checks must pass
verify: lint typecheck test
	@echo "✅ All checks passed."

# Dry-run sync against fixtures (writes nothing)
sync-dry:
	python -c "from tests.mocks import *; from actiondesk.config import load_config; from actiondesk.store import Store; from actiondesk.sync import sync_all; from connectors.gmail_connector import GmailConnector; from connectors.drive_connector import DriveConnector; from connectors.quickbooks_connector import QuickBooksConnector, ReadOnlyQuickBooksClient; import tempfile, os; cfg = load_config(); db = Store(os.path.join(tempfile.gettempdir(), 'dryrun.db')); g = GmailConnector(make_gmail_client(), cfg); d = DriveConnector(make_drive_client(), cfg); qh = make_qb_http_client(); qc = ReadOnlyQuickBooksClient(qh, 'realm', 'https://qb.example.com'); q = QuickBooksConnector(qc, cfg); r = sync_all([g, d, q], db, dry_run=True); print(); [print(f'{s}: {v[\"items_fetched\"]} items fetched (dry-run)') for s,v in r.items()]; db.close()"

# Print sync status
status:
	python -m actiondesk.status

# Clean up
clean:
	rm -f actiondesk.db status.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
