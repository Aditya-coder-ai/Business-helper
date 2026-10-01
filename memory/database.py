"""Database connection manager and transaction controller for Business Memory."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from memory.schema import DDL_STATEMENTS

DEFAULT_MEMORY_DB = Path("memory.db")


class MemoryDatabase:
    """Manages SQLite database lifecycle and atomic transactions for Layer 2."""

    def __init__(self, db_path: Path | str = DEFAULT_MEMORY_DB) -> None:
        self.db_path = Path(db_path)
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,  # Autocommit mode by default; manual transactions with BEGIN
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create all tables and indexes if not already present."""
        with self.transaction():
            for stmt in DDL_STATEMENTS:
                self._conn.execute(stmt)

    @property
    def connection(self) -> sqlite3.Connection:
        """Direct connection reference for low-level cursors."""
        return self._conn

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Atomic transaction context manager.

        Rolls back automatically on any uncaught exception.
        """
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield self._conn
            self._conn.execute("COMMIT")
        except Exception:
            self._conn.execute("ROLLBACK")
            raise

    def execute(self, query: str, params: tuple[Any, ...] | list[Any] = ()) -> sqlite3.Cursor:
        """Execute a query directly using active connection."""
        return self._conn.execute(query, params)

    def close(self) -> None:
        """Close SQLite connection."""
        self._conn.close()

    def __enter__(self) -> MemoryDatabase:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
