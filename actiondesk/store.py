"""SQLite-backed item store with UNIQUE(source, source_item_id) constraint."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from actiondesk.schema import RawItem

DEFAULT_DB = Path("actiondesk.db")


class Store:
    """Thin wrapper around an SQLite database for ingested items."""

    def __init__(self, db_path: Path = DEFAULT_DB) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_table()

    # ------------------------------------------------------------------ DDL
    def _create_table(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id              TEXT PRIMARY KEY,
                source          TEXT NOT NULL,
                source_item_id  TEXT NOT NULL,
                source_url      TEXT NOT NULL DEFAULT '',
                date            TEXT NOT NULL,
                owner           TEXT NOT NULL DEFAULT '',
                content         TEXT NOT NULL DEFAULT '',
                content_hash    TEXT NOT NULL,
                fetched_at      TEXT NOT NULL,
                UNIQUE(source, source_item_id)
            )
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------ DML
    def upsert(self, item: RawItem) -> bool:
        """Insert or update-on-change.  Returns True if a row was written."""
        cur = self._conn.execute(
            "SELECT content_hash FROM items WHERE source = ? AND source_item_id = ?",
            (item.source, item.source_item_id),
        )
        row = cur.fetchone()
        if row is not None and row[0] == item.content_hash:
            return False  # nothing changed

        self._conn.execute(
            """
            INSERT INTO items (id, source, source_item_id, source_url,
                               date, owner, content, content_hash, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source, source_item_id) DO UPDATE SET
                content      = excluded.content,
                content_hash = excluded.content_hash,
                fetched_at   = excluded.fetched_at
            """,
            (
                item.id,
                item.source,
                item.source_item_id,
                item.source_url,
                item.date.isoformat(),
                item.owner,
                item.content,
                item.content_hash,
                item.fetched_at.isoformat(),
            ),
        )
        self._conn.commit()
        return True

    def count(self, source: str | None = None) -> int:
        if source:
            cur = self._conn.execute(
                "SELECT COUNT(*) FROM items WHERE source = ?", (source,)
            )
        else:
            cur = self._conn.execute("SELECT COUNT(*) FROM items")
        return int(cur.fetchone()[0])

    def get(self, source: str, source_item_id: str) -> dict[str, str] | None:
        cur = self._conn.execute(
            "SELECT * FROM items WHERE source = ? AND source_item_id = ?",
            (source, source_item_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row, strict=False))

    def latest_date(self, source: str) -> datetime | None:
        """Return the most recent `date` for a given source, or None."""
        cur = self._conn.execute(
            "SELECT MAX(date) FROM items WHERE source = ?", (source,)
        )
        row = cur.fetchone()
        if row is None or row[0] is None:
            return None
        from dateutil.parser import parse as dtparse

        dt = dtparse(row[0])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def all_items(self, source: str | None = None) -> list[dict[str, str]]:
        if source:
            cur = self._conn.execute(
                "SELECT * FROM items WHERE source = ? ORDER BY date DESC", (source,)
            )
        else:
            cur = self._conn.execute("SELECT * FROM items ORDER BY date DESC")
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row, strict=False)) for row in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()

    # Context-manager support
    def __enter__(self) -> Store:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
