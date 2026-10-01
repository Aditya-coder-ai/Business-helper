"""Tests for Gmail connector."""

from __future__ import annotations

from typing import Any

from connectors.gmail_connector import GmailConnector
from tests.fixtures import GMAIL_EMPTY_MAILBOX
from tests.mocks import make_gmail_client


class TestGmailConnector:
    def test_fetch_yields_items(self, config: dict[str, Any]) -> None:
        client = make_gmail_client()
        conn = GmailConnector(client, config)
        items = list(conn.fetch())
        # msg003 excluded (SPAM), msg004 valid (attachment-only), msg001 duplicate skipped
        # We expect items for msg001, msg002, msg004 (msg001 dup yields same item)
        assert len(items) >= 2

    def test_excluded_labels(self, config: dict[str, Any]) -> None:
        client = make_gmail_client()
        conn = GmailConnector(client, config)
        items = list(conn.fetch())
        source_ids = [i.source_item_id for i in items]
        # msg003 has SPAM label and should be excluded
        assert "msg003" not in source_ids

    def test_empty_mailbox(self, config: dict[str, Any]) -> None:
        client = make_gmail_client(list_response=GMAIL_EMPTY_MAILBOX)
        conn = GmailConnector(client, config)
        items = list(conn.fetch())
        assert items == []

    def test_schema_valid(self, config: dict[str, Any]) -> None:
        client = make_gmail_client()
        conn = GmailConnector(client, config)
        for item in conn.fetch():
            assert item.id
            assert item.source == "gmail"
            assert item.source_item_id
            assert item.date is not None
            assert item.content_hash

    def test_attachment_only_email(self, config: dict[str, Any]) -> None:
        """An email with no body/snippet should still produce a valid item."""
        client = make_gmail_client()
        conn = GmailConnector(client, config)
        items = list(conn.fetch())
        msg004_items = [i for i in items if i.source_item_id == "msg004"]
        assert len(msg004_items) == 1
        assert msg004_items[0].content  # should have at least the subject
