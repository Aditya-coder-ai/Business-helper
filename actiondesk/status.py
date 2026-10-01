"""Print sync status as a formatted table."""

from __future__ import annotations

import json
import sys
from pathlib import Path

STATUS_FILE = Path("status.json")


def print_status(path: Path = STATUS_FILE) -> None:
    if not path.exists():
        print("No status.json found — run a sync first.")
        sys.exit(1)

    with open(path) as f:
        status = json.load(f)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    try:
        from tabulate import tabulate

        rows = []
        for source, info in sorted(status.items()):
            rows.append(
                [
                    source,
                    info.get("status", "?"),
                    info.get("last_sync", "-"),
                    info.get("items_fetched", 0),
                    info.get("error") or "-",
                ]
            )
        print(
            tabulate(
                rows,
                headers=["Source", "Status", "Last Sync", "Items", "Error"],
                tablefmt="simple",
            )
        )
    except ImportError:
        # Fallback without tabulate
        header = f"{'Source':<15} {'Status':<12} {'Last Sync':<28} {'Items':<8} {'Error'}"
        print(header)
        print("-" * len(header))
        for source, info in sorted(status.items()):
            print(
                f"{source:<15} {info.get('status', '?'):<12} "
                f"{info.get('last_sync', '-'):<28} "
                f"{info.get('items_fetched', 0):<8} "
                f"{info.get('error') or '-'}"
            )


if __name__ == "__main__":
    print_status()
