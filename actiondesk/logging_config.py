"""Structured JSON-line logging — no content bodies, no secrets."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Any

# Patterns that should NEVER appear in logs
_SECRET_PATTERNS = re.compile(
    r"(eyJ[A-Za-z0-9_-]{10,})"           # JWT-like tokens
    r"|(AIza[A-Za-z0-9_-]{30,})"          # Google API keys
    r"|([0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com)"  # OAuth client IDs
    r"|(ya29\.[A-Za-z0-9_-]+)"            # Google access tokens
    r"|(1//[A-Za-z0-9_-]+)"               # Google refresh tokens
    r"|(GOCSPX-[A-Za-z0-9_-]+)"           # Google client secrets
    r"|(sk_live_[A-Za-z0-9]+)"            # Stripe-like keys
    r"|(-----BEGIN [A-Z ]+KEY-----)",      # PEM keys
    re.MULTILINE,
)


def _redact(text: str) -> str:
    """Replace anything that looks like a secret with [REDACTED]."""
    return _SECRET_PATTERNS.sub("[REDACTED]", text)


class JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": _redact(record.getMessage()),
        }
        # Attach structured extras if present
        if hasattr(record, "data"):
            raw = getattr(record, "data", None)
            if isinstance(raw, dict):
                safe: dict[str, Any] = {}
                for k, v in raw.items():
                    sv = _redact(str(v)) if isinstance(v, str) else v
                    safe[k] = sv
                payload["data"] = safe
        if record.exc_info and record.exc_info[1]:
            payload["error"] = _redact(str(record.exc_info[1]))
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes JSON lines to stderr."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
    return logger
