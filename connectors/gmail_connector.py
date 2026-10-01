"""Gmail connector — read-only, scope: gmail.readonly."""

from __future__ import annotations

import email.utils
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any, cast

from actiondesk.config import get_exclusions
from actiondesk.logging_config import get_logger
from actiondesk.schema import RawItem, content_hash, make_id
from connectors.base import BaseConnector

logger = get_logger(__name__)


class GmailConnector(BaseConnector):
    """Fetches messages from Gmail using the API client.

    In production, `api_client` is a googleapiclient.discovery.Resource.
    In tests, it's a mock that returns fixture data.
    """

    source_name = "gmail"

    def __init__(self, api_client: Any, config: dict[str, Any]) -> None:
        self._client = api_client
        self._config = config
        self._exclusions = get_exclusions(config, "gmail")

    # ------------------------------------------------------------------ public
    def fetch(self, since: datetime | None = None) -> Iterator[RawItem]:
        """Yield RawItems for messages newer than *since*."""
        query = ""
        if since:
            # Gmail uses epoch seconds for after: filter
            epoch = int(since.timestamp())
            query = f"after:{epoch}"

        logger.info("gmail.fetch start", extra={"data": {"query": query}})

        try:
            message_ids = self._list_message_ids(query)
        except Exception:
            logger.exception("gmail.fetch list failed")
            raise

        for mid in message_ids:
            try:
                msg = self._get_message(mid)
                if msg is None:
                    continue
                item = self._to_raw_item(msg)
                if item is None:
                    continue
                if self._is_excluded(msg):
                    logger.debug(
                        "gmail.skip excluded",
                        extra={"data": {"message_id": mid}},
                    )
                    continue
                yield item
            except Exception:
                logger.exception("gmail.fetch message failed", extra={"data": {"id": mid}})
                continue

    # ------------------------------------------------------------------ private
    def _list_message_ids(self, query: str) -> list[str]:
        result = self._client.users().messages().list(userId="me", q=query).execute()
        messages = result.get("messages", [])
        return [m["id"] for m in messages]

    def _get_message(self, message_id: str) -> dict[str, Any] | None:
        try:
            res = (
                self._client.users()
                .messages()
                .get(userId="me", id=message_id, format="metadata")
                .execute()
            )
            return cast(dict[str, Any], res) if isinstance(res, dict) else None
        except Exception:
            logger.exception("gmail.get_message failed", extra={"data": {"id": message_id}})
            return None

    def _to_raw_item(self, msg: dict[str, Any]) -> RawItem | None:
        """Convert a Gmail API message dict to a RawItem."""
        msg_id = msg.get("id", "")
        if not msg_id:
            return None

        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }

        subject = headers.get("subject", "(no subject)")
        snippet = msg.get("snippet", "")
        body = f"{subject}\n{snippet}" if snippet else subject

        # Parse date from headers
        date_str = headers.get("date", "")
        if date_str:
            parsed = email.utils.parsedate_to_datetime(date_str)
        else:
            # Fall back to internalDate (ms since epoch)
            internal = msg.get("internalDate", "0")
            parsed = datetime.fromtimestamp(int(internal) / 1000, tz=timezone.utc)

        owner = headers.get("from", "")
        sid = make_id("gmail", msg_id)

        return RawItem(
            id=sid,
            source="gmail",
            source_item_id=msg_id,
            source_url=f"https://mail.google.com/mail/u/0/#inbox/{msg_id}",
            date=parsed,
            owner=owner,
            content=body,
            content_hash=content_hash(body),
        )

    def _is_excluded(self, msg: dict[str, Any]) -> bool:
        """Check if this message matches any exclusion rule."""
        # Label exclusions
        excluded_labels = set(self._exclusions.get("labels", []))
        msg_labels = set(msg.get("labelIds", []))
        if excluded_labels & msg_labels:
            return True

        # From-address exclusions
        excluded_from = set(self._exclusions.get("from_addresses", []))
        headers = {
            h["name"].lower(): h["value"]
            for h in msg.get("payload", {}).get("headers", [])
        }
        from_addr = headers.get("from", "")
        for excl in excluded_from:
            if excl.lower() in from_addr.lower():
                return True

        return False
