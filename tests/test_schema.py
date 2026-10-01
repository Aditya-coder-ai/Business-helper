"""Tests for the schema module."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from actiondesk.schema import RawItem, content_hash, make_id


class TestMakeId:
    def test_deterministic(self) -> None:
        assert make_id("gmail", "abc") == make_id("gmail", "abc")

    def test_different_sources(self) -> None:
        assert make_id("gmail", "x") != make_id("drive", "x")


class TestContentHash:
    def test_consistent(self) -> None:
        assert content_hash("hello") == content_hash("hello")

    def test_different(self) -> None:
        assert content_hash("a") != content_hash("b")


class TestRawItem:
    def test_valid(self) -> None:
        item = RawItem(
            id="abc123",
            source="gmail",
            source_item_id="msg001",
            date=datetime(2023, 9, 18, tzinfo=timezone.utc),
            content="test",
            content_hash=content_hash("test"),
        )
        assert item.source == "gmail"

    def test_empty_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RawItem(
                id="",
                source="gmail",
                source_item_id="msg001",
                date=datetime.now(timezone.utc),
                content="x",
                content_hash="x" * 64,
            )

    def test_empty_source_item_id_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RawItem(
                id="abc",
                source="gmail",
                source_item_id="",
                date=datetime.now(timezone.utc),
                content="x",
                content_hash="x" * 64,
            )

    def test_invalid_source_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RawItem(
                id="abc",
                source="twitter",
                source_item_id="123",
                date=datetime.now(timezone.utc),
                content="x",
                content_hash="x" * 64,
            )

    def test_date_string_parsed(self) -> None:
        item = RawItem(
            id="abc",
            source="gmail",
            source_item_id="123",
            date="2023-09-18T12:00:00+00:00",
            content="x",
            content_hash=content_hash("x"),
        )
        assert isinstance(item.date, datetime)

    def test_naive_date_gets_utc(self) -> None:
        item = RawItem(
            id="abc",
            source="drive",
            source_item_id="123",
            date="2023-09-18T12:00:00",
            content="x",
            content_hash=content_hash("x"),
        )
        assert item.date.tzinfo is not None
