"""conftest.py — shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
import yaml

from actiondesk.store import Store


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Generator[Store, None, None]:
    """Provide a fresh SQLite store in a temp directory."""
    db_path = tmp_path / "test.db"
    store = Store(db_path)
    yield store
    store.close()


@pytest.fixture()
def config() -> dict[str, Any]:
    """Load the project config.yaml."""
    cfg_path = Path(__file__).resolve().parent.parent / "config.yaml"
    with open(cfg_path) as f:
        cfg: dict[str, Any] = yaml.safe_load(f)
        return cfg


@pytest.fixture()
def tmp_status(tmp_path: Path) -> Path:
    """Return path for a temporary status.json."""
    return tmp_path / "status.json"
