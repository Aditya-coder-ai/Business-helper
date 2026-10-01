"""QuickBooks connector — read-only guard wrapping the HTTP client.

QuickBooks has no read-only scope, so we wrap the client in a class that
only exposes GET/query methods and raises on any mutating HTTP verb.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any

from actiondesk.config import get_exclusions
from actiondesk.logging_config import get_logger
from actiondesk.schema import RawItem, content_hash, make_id
from connectors.base import BaseConnector

logger = get_logger(__name__)


class ReadOnlyQuickBooksClient:
    """Wrapper that ONLY allows GET requests.  Any other verb raises."""

    def __init__(self, http_client: Any, realm_id: str, base_url: str) -> None:
        self._http = http_client
        self._realm_id = realm_id
        self._base_url = base_url.rstrip("/")

    def get(self, path: str, **kwargs: Any) -> Any:
        url = f"{self._base_url}/v3/company/{self._realm_id}/{path}"
        logger.debug("quickbooks.GET", extra={"data": {"path": path}})
        return self._http.get(url, **kwargs)

    def query(self, sql: str, **kwargs: Any) -> Any:
        """Execute a QuickBooks query (read-only SQL-like syntax)."""
        url = f"{self._base_url}/v3/company/{self._realm_id}/query"
        params = {"query": sql}
        logger.debug("quickbooks.query", extra={"data": {"sql": sql}})
        return self._http.get(url, params=params, **kwargs)

    # Block all writes
    def post(self, *args: Any, **kwargs: Any) -> Any:
        raise PermissionError("WRITE BLOCKED: QuickBooks connector is read-only (POST)")

    def put(self, *args: Any, **kwargs: Any) -> Any:
        raise PermissionError("WRITE BLOCKED: QuickBooks connector is read-only (PUT)")

    def patch(self, *args: Any, **kwargs: Any) -> Any:
        raise PermissionError("WRITE BLOCKED: QuickBooks connector is read-only (PATCH)")

    def delete(self, *args: Any, **kwargs: Any) -> Any:
        raise PermissionError("WRITE BLOCKED: QuickBooks connector is read-only (DELETE)")


class QuickBooksConnector(BaseConnector):
    """Fetches invoices and customers from QuickBooks.

    Takes a ReadOnlyQuickBooksClient (or mock in tests).
    """

    source_name = "quickbooks"

    # Entity types we ingest
    ENTITY_TYPES = ["Invoice", "Customer", "Payment", "Bill"]

    def __init__(self, client: ReadOnlyQuickBooksClient, config: dict[str, Any]) -> None:
        self._client = client
        self._config = config
        self._exclusions = get_exclusions(config, "quickbooks")

    # ------------------------------------------------------------------ public
    def fetch(self, since: datetime | None = None) -> Iterator[RawItem]:
        excluded_types = set(self._exclusions.get("entity_types", []))
        active_types = [et for et in self.ENTITY_TYPES if et not in excluded_types]

        for et in self.ENTITY_TYPES:
            if et in excluded_types:
                logger.debug(
                    "quickbooks.skip excluded entity_type",
                    extra={"data": {"entity_type": et}},
                )

        errors: list[Exception] = []

        for entity_type in active_types:
            try:
                yield from self._fetch_entity(entity_type, since)
            except StopIteration:
                pass
            except Exception as exc:
                logger.exception(
                    "quickbooks.fetch entity failed",
                    extra={"data": {"entity_type": entity_type}},
                )
                errors.append(exc)
                continue

        # If ALL active entity types failed, propagate the first error
        if errors and len(errors) == len(active_types):
            raise errors[0]

    # ------------------------------------------------------------------ private
    def _fetch_entity(
        self, entity_type: str, since: datetime | None
    ) -> Iterator[RawItem]:
        sql = f"SELECT * FROM {entity_type}"
        if since:
            ts = since.strftime("%Y-%m-%dT%H:%M:%S")
            sql += f" WHERE MetaData.LastUpdatedTime > '{ts}'"

        logger.info(
            "quickbooks.query",
            extra={"data": {"entity_type": entity_type, "sql": sql}},
        )

        response = self._client.query(sql)

        # Handle mock/real response
        if hasattr(response, "json"):
            data = response.json()
        elif isinstance(response, dict):
            data = response
        else:
            logger.error("quickbooks.unexpected response type")
            return

        query_response = data.get("QueryResponse", {})
        entities = query_response.get(entity_type, [])

        for entity in entities:
            item = self._to_raw_item(entity, entity_type)
            if item is not None:
                yield item

    def _to_raw_item(self, entity: dict[str, Any], entity_type: str) -> RawItem | None:
        eid = entity.get("Id", "")
        if not eid:
            return None

        source_item_id = f"{entity_type}:{eid}"

        # Build content string
        if entity_type == "Invoice":
            body = f"Invoice #{entity.get('DocNumber', '?')} — ${entity.get('TotalAmt', 0)}"
        elif entity_type == "Customer":
            body = f"Customer: {entity.get('DisplayName', '?')}"
        elif entity_type == "Payment":
            body = f"Payment ${entity.get('TotalAmt', 0)}"
        elif entity_type == "Bill":
            body = f"Bill #{entity.get('DocNumber', '?')} — ${entity.get('TotalAmt', 0)}"
        else:
            body = f"{entity_type} {eid}"

        # Date
        meta = entity.get("MetaData", {})
        date_str = meta.get("LastUpdatedTime", "") or meta.get("CreateTime", "")
        if date_str:
            from dateutil.parser import parse as dtparse

            date = dtparse(date_str)
        else:
            date = datetime.now(timezone.utc)

        sid = make_id("quickbooks", source_item_id)

        return RawItem(
            id=sid,
            source="quickbooks",
            source_item_id=source_item_id,
            source_url="",
            date=date,
            owner="",
            content=body,
            content_hash=content_hash(body),
        )
