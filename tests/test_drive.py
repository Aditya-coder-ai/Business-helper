"""Tests for Drive connector."""

from __future__ import annotations

from typing import Any

from connectors.drive_connector import DriveConnector
from tests.fixtures import DRIVE_EMPTY_LIST
from tests.mocks import make_drive_client


class TestDriveConnector:
    def test_fetch_yields_items(self, config: dict[str, Any]) -> None:
        client = make_drive_client()
        conn = DriveConnector(client, config)
        items = list(conn.fetch())
        # file003_excluded (name "Private"), file004_deleted (trashed)
        assert len(items) == 2

    def test_excluded_path(self, config: dict[str, Any]) -> None:
        client = make_drive_client()
        conn = DriveConnector(client, config)
        items = list(conn.fetch())
        ids = [i.source_item_id for i in items]
        assert "file003_excluded" not in ids

    def test_trashed_excluded(self, config: dict[str, Any]) -> None:
        client = make_drive_client()
        conn = DriveConnector(client, config)
        items = list(conn.fetch())
        ids = [i.source_item_id for i in items]
        assert "file004_deleted" not in ids

    def test_empty_list(self, config: dict[str, Any]) -> None:
        client = make_drive_client(list_response=DRIVE_EMPTY_LIST)
        conn = DriveConnector(client, config)
        assert list(conn.fetch()) == []

    def test_schema_valid(self, config: dict[str, Any]) -> None:
        client = make_drive_client()
        conn = DriveConnector(client, config)
        for item in conn.fetch():
            assert item.id
            assert item.source == "drive"
            assert item.source_item_id
            assert item.date is not None
            assert item.content_hash
