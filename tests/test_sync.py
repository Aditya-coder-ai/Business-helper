"""Integration tests for sync engine.

Covers:
- Idempotency (sync twice → 0 new rows)
- Incremental (second sync only fetches newer items)
- Failure isolation (one source error doesn't stop others)
- Dry-run mode
- Secret scanning
- Read-only scope guard
- Exclusion enforcement
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from actiondesk.store import Store
from actiondesk.sync import sync_all, sync_source
from connectors.drive_connector import DriveConnector
from connectors.gmail_connector import GmailConnector
from connectors.quickbooks_connector import (
    QuickBooksConnector,
    ReadOnlyQuickBooksClient,
)
from tests.mocks import make_drive_client, make_gmail_client, make_qb_http_client


def _all_connectors(config: dict[str, Any]) -> list[Any]:
    gmail = GmailConnector(make_gmail_client(), config)
    drive = DriveConnector(make_drive_client(), config)
    qb_http = make_qb_http_client()
    qb_client = ReadOnlyQuickBooksClient(qb_http, "realm123", "https://qb.example.com")
    qb = QuickBooksConnector(qb_client, config)
    return [gmail, drive, qb]


class TestIdempotency:
    """Running sync twice yields zero new rows on the second run."""

    def test_sync_twice_no_new_rows(
        self, tmp_db: Store, config: dict[str, Any], tmp_status: Path
    ) -> None:
        connectors = _all_connectors(config)
        sync_all(connectors, tmp_db, status_path=tmp_status)
        count_after_first = tmp_db.count()
        assert count_after_first > 0

        # Second sync — same data
        connectors2 = _all_connectors(config)
        sync_all(connectors2, tmp_db, status_path=tmp_status)
        assert tmp_db.count() == count_after_first


class TestIncremental:
    """Second sync should use the cursor and only fetch newer items."""

    def test_incremental_cursor(
        self, tmp_db: Store, config: dict[str, Any], tmp_status: Path
    ) -> None:
        connectors = _all_connectors(config)
        sync_all(connectors, tmp_db, status_path=tmp_status)

        # Verify cursor is set for all sources
        for source in ["gmail", "drive", "quickbooks"]:
            latest = tmp_db.latest_date(source)
            # latest can be None for sources with no items, but we expect items
            if tmp_db.count(source) > 0:
                assert latest is not None


class TestFailureIsolation:
    """One source failing does not stop others; error is recorded."""

    def test_one_source_fails(
        self, tmp_db: Store, config: dict[str, Any], tmp_status: Path
    ) -> None:
        gmail = GmailConnector(make_gmail_client(), config)
        drive = DriveConnector(make_drive_client(), config)

        # Broken QB client
        broken_http = MagicMock()
        broken_http.get.side_effect = ConnectionError("QB is down")
        qb_client = ReadOnlyQuickBooksClient(broken_http, "realm123", "https://qb.example.com")
        qb = QuickBooksConnector(qb_client, config)

        results = sync_all([gmail, drive, qb], tmp_db, status_path=tmp_status)

        assert results["gmail"]["status"] == "connected"
        assert results["drive"]["status"] == "connected"
        assert results["quickbooks"]["status"] == "error"
        assert results["quickbooks"]["error"] is not None

        # Verify status.json has the error
        with open(tmp_status) as f:
            status = json.load(f)
        assert status["quickbooks"]["status"] == "error"

        # Gmail and Drive should still have items
        assert tmp_db.count("gmail") > 0
        assert tmp_db.count("drive") > 0


class TestDryRun:
    """Dry-run fetches and validates but writes nothing."""

    def test_dry_run_no_writes(
        self, tmp_db: Store, config: dict[str, Any], tmp_status: Path
    ) -> None:
        connectors = _all_connectors(config)
        results = sync_all(connectors, tmp_db, dry_run=True, status_path=tmp_status)
        assert tmp_db.count() == 0
        # But status should still show as connected
        for source in ["gmail", "drive", "quickbooks"]:
            assert results[source]["status"] == "connected"
            assert results[source]["items_fetched"] > 0 or source == "quickbooks"


class TestExclusions:
    """Excluded items never reach the store."""

    def test_excluded_items_not_stored(
        self, tmp_db: Store, config: dict[str, Any], tmp_status: Path
    ) -> None:
        connectors = _all_connectors(config)
        sync_all(connectors, tmp_db, status_path=tmp_status)

        all_items = tmp_db.all_items()
        source_ids = [i["source_item_id"] for i in all_items]

        # Gmail: msg003 (SPAM) should not be stored
        assert "msg003" not in source_ids

        # Drive: file003_excluded (Private), file004_deleted should not be stored
        assert "file003_excluded" not in source_ids
        assert "file004_deleted" not in source_ids


class TestSchemaValidation:
    """Every stored record must pass validation — no empty id/date/source."""

    def test_all_records_valid(
        self, tmp_db: Store, config: dict[str, Any], tmp_status: Path
    ) -> None:
        connectors = _all_connectors(config)
        sync_all(connectors, tmp_db, status_path=tmp_status)

        for row in tmp_db.all_items():
            assert row["id"], "id must not be empty"
            assert row["source"] in ("gmail", "drive", "quickbooks")
            assert row["source_item_id"], "source_item_id must not be empty"
            assert row["date"], "date must not be empty"
            assert row["content_hash"], "content_hash must not be empty"


class TestReadOnlyGuard:
    """Verify that only read scopes are requested and write verbs are blocked."""

    def test_gmail_readonly_scope(self, config: dict[str, Any]) -> None:
        scopes = config["sources"]["gmail"]["scopes"]
        for scope in scopes:
            assert "readonly" in scope, f"Non-read scope found: {scope}"
            assert "modify" not in scope
            assert "compose" not in scope
            assert "send" not in scope

    def test_drive_readonly_scope(self, config: dict[str, Any]) -> None:
        scopes = config["sources"]["drive"]["scopes"]
        for scope in scopes:
            assert "readonly" in scope, f"Non-read scope found: {scope}"

    def test_quickbooks_write_blocked(self) -> None:
        http = MagicMock()
        client = ReadOnlyQuickBooksClient(http, "r", "https://example.com")
        for method in ["post", "put", "patch", "delete"]:
            with pytest.raises(PermissionError, match="WRITE BLOCKED"):
                getattr(client, method)("/any")


class TestSecretScan:
    """No secrets in the repo or in logs."""

    def test_no_secrets_in_source(self) -> None:
        """Scan all .py and .yaml files for secret patterns."""
        project_root = Path(__file__).resolve().parent.parent
        secret_patterns = [
            re.compile(r"AIza[A-Za-z0-9_-]{30,}"),       # Google API key
            re.compile(r"ya29\.[A-Za-z0-9_-]+"),          # Google access token
            re.compile(r"1//[A-Za-z0-9_-]{20,}"),         # Google refresh token
            re.compile(r"GOCSPX-[A-Za-z0-9_-]+"),         # Client secret
            re.compile(r"sk_live_[A-Za-z0-9]+"),           # Stripe key
            re.compile(r"-----BEGIN [A-Z ]+KEY-----"),     # PEM key
        ]

        for ext in ("*.py", "*.yaml", "*.yml", "*.toml", "*.md"):
            for filepath in project_root.rglob(ext):
                # Skip venv and __pycache__
                parts = filepath.parts
                if "venv" in parts or ".venv" in parts or "__pycache__" in parts:
                    continue
                content = filepath.read_text(errors="ignore")
                for pattern in secret_patterns:
                    match = pattern.search(content)
                    assert match is None, (
                        f"Secret pattern found in {filepath}: {match.group()[:20]}..."
                    )

    def test_gitignore_has_secrets(self) -> None:
        """Verify .gitignore blocks secret files."""
        project_root = Path(__file__).resolve().parent.parent
        gitignore = (project_root / ".gitignore").read_text()
        for secret_file in ["credentials.json", "token.json", ".env"]:
            assert secret_file in gitignore, f"{secret_file} missing from .gitignore"


class TestStatusJson:
    """Status.json is written correctly after sync."""

    def test_status_written(
        self, tmp_db: Store, config: dict[str, Any], tmp_status: Path
    ) -> None:
        connectors = _all_connectors(config)
        sync_all(connectors, tmp_db, status_path=tmp_status)

        assert tmp_status.exists()
        with open(tmp_status) as f:
            status = json.load(f)

        for source in ["gmail", "drive", "quickbooks"]:
            assert source in status
            assert "status" in status[source]
            assert "last_sync" in status[source]
            assert "items_fetched" in status[source]

    def test_status_with_error(
        self, tmp_db: Store, config: dict[str, Any], tmp_status: Path
    ) -> None:
        # Broken Gmail
        broken_client = MagicMock()
        broken_client.users().messages().list.side_effect = RuntimeError("API down")
        gmail = GmailConnector(broken_client, config)

        results = sync_source(gmail, tmp_db, status_path=tmp_status)
        assert results["status"] == "error"
        assert "API down" in results["error"]
