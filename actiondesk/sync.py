"""Incremental sync engine — fetches from all sources, stores in SQLite, writes status.json."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

from actiondesk.logging_config import get_logger
from actiondesk.schema import RawItem
from actiondesk.store import Store
from connectors.base import BaseConnector

logger = get_logger(__name__)

STATUS_FILE = Path("status.json")


def _load_status(path: Path = STATUS_FILE) -> dict[str, Any]:
    if path.exists():
        with open(path) as f:
            data = json.load(f)
            return cast(dict[str, Any], data) if isinstance(data, dict) else {}
    return {}


def _save_status(status: dict[str, Any], path: Path = STATUS_FILE) -> None:
    with open(path, "w") as f:
        json.dump(status, f, indent=2, default=str)


def sync_source(
    connector: BaseConnector,
    store: Store,
    dry_run: bool = False,
    status_path: Path = STATUS_FILE,
) -> dict[str, Any]:
    """Run incremental sync for one source. Returns its status entry."""
    source = connector.source_name
    status = _load_status(status_path)
    entry: dict[str, Any] = {
        "status": "syncing",
        "last_sync": datetime.now(timezone.utc).isoformat(),
        "items_fetched": 0,
        "error": None,
    }
    status[source] = entry
    _save_status(status, status_path)

    try:
        # Incremental: use latest date from store as cursor
        since = store.latest_date(source)
        logger.info(
            "sync.start",
            extra={"data": {"source": source, "since": str(since), "dry_run": dry_run}},
        )

        fetched = 0
        written = 0
        for item in connector.fetch(since):
            fetched += 1
            if not dry_run:
                if store.upsert(item):
                    written += 1
            else:
                # Validate the item even in dry-run
                RawItem.model_validate(item.model_dump())
                logger.info(
                    "sync.dry_run item",
                    extra={"data": {"source": source, "item_id": item.source_item_id}},
                )

        entry["status"] = "connected"
        entry["items_fetched"] = fetched
        entry["items_written"] = written
        logger.info(
            "sync.done",
            extra={"data": {"source": source, "fetched": fetched, "written": written}},
        )

    except Exception as exc:
        entry["status"] = "error"
        entry["error"] = str(exc)
        logger.exception("sync.error", extra={"data": {"source": source}})

    entry["last_sync"] = datetime.now(timezone.utc).isoformat()
    status[source] = entry
    _save_status(status, status_path)
    return entry


def sync_all(
    connectors: list[BaseConnector],
    store: Store,
    dry_run: bool = False,
    status_path: Path = STATUS_FILE,
) -> dict[str, Any]:
    """Sync all sources.  One failure does NOT stop others."""
    results: dict[str, Any] = {}
    for conn in connectors:
        results[conn.source_name] = sync_source(
            conn, store, dry_run=dry_run, status_path=status_path
        )
    return results


def main() -> None:
    """CLI to trigger live or dry-run sync."""
    import argparse
    import sys

    from actiondesk.config import load_config

    parser = argparse.ArgumentParser(description="ActionDesk Ingestion Sync")
    parser.add_argument(
        "--source",
        choices=["gmail", "drive", "all"],
        default="all",
        help="Source to sync (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without writing to the store",
    )
    parser.add_argument(
        "--db",
        default="actiondesk.db",
        help="Path to SQLite database (default: actiondesk.db)",
    )
    args = parser.parse_args()

    cfg = load_config()
    db = Store(args.db)
    connectors: list[BaseConnector] = []

    if args.source in ("gmail", "all"):
        try:
            from actiondesk.auth import get_gmail_service
            from connectors.gmail_connector import GmailConnector

            service = get_gmail_service()
            connectors.append(GmailConnector(service, cfg))
        except Exception as exc:
            logger.warning(
                "sync.cli_source_init_failed",
                extra={"data": {"source": "gmail", "error": str(exc)}},
            )
            print(f"Skipping Gmail: {exc}")

    if args.source in ("drive", "all"):
        try:
            from actiondesk.auth import get_drive_service
            from connectors.drive_connector import DriveConnector

            service = get_drive_service()
            connectors.append(DriveConnector(service, cfg))
        except Exception as exc:
            logger.warning(
                "sync.cli_source_init_failed",
                extra={"data": {"source": "drive", "error": str(exc)}},
            )
            print(f"Skipping Drive: {exc}")

    if not connectors:
        print("No connectors initialized to sync.")
        db.close()
        sys.exit(1)

    print(f"Starting sync ({'dry-run' if args.dry_run else 'live'})...")
    results = sync_all(connectors, db, dry_run=args.dry_run)
    db.close()

    for s, v in results.items():
        print(
            f"  {s}: status={v.get('status')} "
            f"fetched={v.get('items_fetched')} "
            f"written={v.get('items_written', 0)}"
        )


if __name__ == "__main__":
    main()

