"""Abstract base for all connectors."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from actiondesk.logging_config import get_logger
from actiondesk.schema import RawItem

logger = get_logger(__name__)

# Retry config
MAX_RETRIES = 4
BACKOFF_BASE = 2.0   # seconds
RETRYABLE_CODES = {429, 500, 502, 503, 504}


class BaseConnector(ABC):
    """Every connector must implement `fetch(since) -> Iterator[RawItem]`."""

    source_name: str = ""

    @abstractmethod
    def fetch(self, since: datetime | None = None) -> Iterator[RawItem]:
        """Yield RawItems newer than *since*.  If since is None, fetch all."""
        ...

    @staticmethod
    def retry_on_error(func: Any) -> Any:
        """Decorator: exponential backoff on 429/5xx."""
        import functools

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    status_code = getattr(exc, "status_code", None) or getattr(
                        getattr(exc, "response", None), "status_code", None
                    )
                    if status_code and int(status_code) in RETRYABLE_CODES:
                        wait = BACKOFF_BASE ** attempt
                        logger.warning(
                            "Retryable error %s, attempt %d/%d, waiting %.1fs",
                            status_code,
                            attempt,
                            MAX_RETRIES,
                            wait,
                            extra={"data": {"status": status_code, "attempt": attempt}},
                        )
                        time.sleep(wait)
                        last_exc = exc
                        continue
                    raise
            raise last_exc  # type: ignore[misc]

        return wrapper
