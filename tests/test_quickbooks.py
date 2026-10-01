"""Tests for QuickBooks connector — including read-only guard."""

from __future__ import annotations

from typing import Any

import pytest

from connectors.quickbooks_connector import (
    QuickBooksConnector,
    ReadOnlyQuickBooksClient,
)
from tests.mocks import make_qb_http_client


class TestReadOnlyGuard:
    """Any write call must raise PermissionError."""

    def test_post_blocked(self) -> None:
        http = make_qb_http_client()
        client = ReadOnlyQuickBooksClient(http, "realm123", "https://qb.example.com")
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            client.post("/some/path")

    def test_put_blocked(self) -> None:
        http = make_qb_http_client()
        client = ReadOnlyQuickBooksClient(http, "realm123", "https://qb.example.com")
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            client.put("/some/path")

    def test_patch_blocked(self) -> None:
        http = make_qb_http_client()
        client = ReadOnlyQuickBooksClient(http, "realm123", "https://qb.example.com")
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            client.patch("/some/path")

    def test_delete_blocked(self) -> None:
        http = make_qb_http_client()
        client = ReadOnlyQuickBooksClient(http, "realm123", "https://qb.example.com")
        with pytest.raises(PermissionError, match="WRITE BLOCKED"):
            client.delete("/some/path")

    def test_get_allowed(self) -> None:
        http = make_qb_http_client()
        client = ReadOnlyQuickBooksClient(http, "realm123", "https://qb.example.com")
        # Should not raise
        client.get("companyinfo/realm123")

    def test_query_allowed(self) -> None:
        http = make_qb_http_client()
        client = ReadOnlyQuickBooksClient(http, "realm123", "https://qb.example.com")
        client.query("SELECT * FROM Invoice")


class TestQuickBooksConnector:
    def _make_connector(self, config: dict[str, Any]) -> QuickBooksConnector:
        http = make_qb_http_client()
        client = ReadOnlyQuickBooksClient(http, "realm123", "https://qb.example.com")
        return QuickBooksConnector(client, config)

    def test_fetch_yields_items(self, config: dict[str, Any]) -> None:
        conn = self._make_connector(config)
        items = list(conn.fetch())
        # 2 invoices + 1 customer + 0 payments + 0 bills = 3
        assert len(items) == 3

    def test_schema_valid(self, config: dict[str, Any]) -> None:
        conn = self._make_connector(config)
        for item in conn.fetch():
            assert item.id
            assert item.source == "quickbooks"
            assert item.source_item_id
            assert item.date is not None
            assert item.content_hash

    def test_invoice_content(self, config: dict[str, Any]) -> None:
        conn = self._make_connector(config)
        items = list(conn.fetch())
        invoices = [i for i in items if "Invoice" in i.source_item_id]
        assert len(invoices) == 2
        assert "INV-1001" in invoices[0].content
