"""Tests for the SQLite store."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from actiondesk.schema import RawItem, content_hash, make_id
from actiondesk.store import Store


def _make_item(
    source: Literal["gmail", "drive", "quickbooks"] = "gmail",
    sid: str = "test1",
    content: str = "hello",
) -> RawItem:
    return RawItem(
        id=make_id(source, sid),
        source=source,
        source_item_id=sid,
        date=datetime(2023, 9, 18, tzinfo=timezone.utc),
        content=content,
        content_hash=content_hash(content),
    )


class TestStore:
    def test_upsert_new(self, tmp_db: Store) -> None:
        item = _make_item()
        assert tmp_db.upsert(item) is True
        assert tmp_db.count() == 1

    def test_upsert_idempotent(self, tmp_db: Store) -> None:
        item = _make_item()
        tmp_db.upsert(item)
        assert tmp_db.upsert(item) is False  # same content_hash
        assert tmp_db.count() == 1

    def test_upsert_changed(self, tmp_db: Store) -> None:
        item1 = _make_item(content="v1")
        tmp_db.upsert(item1)
        item2 = _make_item(content="v2")  # different content
        assert tmp_db.upsert(item2) is True
        assert tmp_db.count() == 1  # still one row, updated

    def test_unique_constraint(self, tmp_db: Store) -> None:
        tmp_db.upsert(_make_item(source="gmail", sid="a"))
        tmp_db.upsert(_make_item(source="drive", sid="a"))
        assert tmp_db.count() == 2  # different sources

    def test_latest_date(self, tmp_db: Store) -> None:
        tmp_db.upsert(_make_item(source="gmail", sid="a"))
        latest = tmp_db.latest_date("gmail")
        assert latest is not None
        assert latest.year == 2023

    def test_latest_date_none(self, tmp_db: Store) -> None:
        assert tmp_db.latest_date("gmail") is None

    def test_get(self, tmp_db: Store) -> None:
        tmp_db.upsert(_make_item(source="gmail", sid="x"))
        row = tmp_db.get("gmail", "x")
        assert row is not None
        assert row["source_item_id"] == "x"

    def test_get_missing(self, tmp_db: Store) -> None:
        assert tmp_db.get("gmail", "nope") is None
