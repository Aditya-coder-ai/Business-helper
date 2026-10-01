"""Google Drive connector — read-only, scope: drive.readonly."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any, cast

from actiondesk.config import get_exclusions
from actiondesk.logging_config import get_logger
from actiondesk.schema import RawItem, content_hash, make_id
from connectors.base import BaseConnector

logger = get_logger(__name__)


class DriveConnector(BaseConnector):
    """Fetches file metadata from Google Drive.

    In production, `api_client` is a googleapiclient.discovery.Resource.
    In tests, it's a mock.
    """

    source_name = "drive"

    def __init__(self, api_client: Any, config: dict[str, Any]) -> None:
        self._client = api_client
        self._config = config
        self._exclusions = get_exclusions(config, "drive")

    # ------------------------------------------------------------------ public
    def fetch(self, since: datetime | None = None) -> Iterator[RawItem]:
        query_parts = ["trashed = false"]
        if since:
            ts = since.strftime("%Y-%m-%dT%H:%M:%S")
            query_parts.append(f"modifiedTime > '{ts}'")

        q = " and ".join(query_parts)
        logger.info("drive.fetch start", extra={"data": {"query": q}})

        try:
            files = self._list_files(q)
        except Exception:
            logger.exception("drive.fetch list failed")
            raise

        for f in files:
            try:
                item = self._to_raw_item(f)
                if item is None:
                    continue
                if self._is_excluded(f):
                    logger.debug(
                        "drive.skip excluded",
                        extra={"data": {"file_id": f.get("id")}},
                    )
                    continue
                yield item
            except Exception:
                logger.exception("drive.fetch file failed", extra={"data": {"id": f.get("id")}})
                continue

    # ------------------------------------------------------------------ private
    def _list_files(self, query: str) -> list[dict[str, Any]]:
        result = (
            self._client.files()
            .list(
                q=query,
                fields="files(id,name,mimeType,modifiedTime,owners,webViewLink,parents)",
                pageSize=100,
            )
            .execute()
        )
        files = result.get("files", [])
        return cast(list[dict[str, Any]], files) if isinstance(files, list) else []

    def _to_raw_item(self, f: dict[str, Any]) -> RawItem | None:
        file_id = f.get("id", "")
        if not file_id:
            return None

        name = f.get("name", "(untitled)")
        mime = f.get("mimeType", "")
        body = f"{name} [{mime}]"

        mod_time = f.get("modifiedTime", "")
        if mod_time:
            from dateutil.parser import parse as dtparse

            date = dtparse(mod_time)
        else:
            date = datetime.now(timezone.utc)

        owners = f.get("owners", [])
        owner = owners[0].get("emailAddress", "") if owners else ""

        link = f.get("webViewLink", "")
        sid = make_id("drive", file_id)

        return RawItem(
            id=sid,
            source="drive",
            source_item_id=file_id,
            source_url=link,
            date=date,
            owner=owner,
            content=body,
            content_hash=content_hash(body),
        )

    def _is_excluded(self, f: dict[str, Any]) -> bool:
        # Path exclusions (check parent folder names — simplified)
        excluded_paths = self._exclusions.get("paths", [])
        name = f.get("name", "")
        for ep in excluded_paths:
            # Strip leading slash for comparison
            ep_name = ep.strip("/")
            if name == ep_name:
                return True

        # MIME-type exclusions
        excluded_mimes = set(self._exclusions.get("mime_types", []))
        if f.get("mimeType", "") in excluded_mimes:
            return True

        # Trashed files (belt-and-suspenders)
        if f.get("trashed", False):
            return True

        return False
