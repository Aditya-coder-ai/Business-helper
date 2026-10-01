"""Load and validate config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Read config.yaml and return the parsed dict."""
    p = path or _DEFAULT_PATH
    with open(p) as f:
        cfg: dict[str, Any] = yaml.safe_load(f)
    return cfg


def get_exclusions(cfg: dict[str, Any], source: str) -> dict[str, Any]:
    """Return the exclusions dict for a given source."""
    res = cfg.get("exclusions", {}).get(source, {})
    return cast(dict[str, Any], res) if isinstance(res, dict) else {}
