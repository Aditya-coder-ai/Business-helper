"""Run script for the ActionDesk Layer 2 FastAPI backend server."""

from __future__ import annotations

import argparse
import socket
import sys
from pathlib import Path

import uvicorn

from memory.seed import seed_database


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a local port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="ActionDesk Business Memory Backend Server")
    parser.add_argument(
        "--port", type=int, default=None, help="Port to run on (default: 8000 or 8001)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host address to bind (default: 127.0.0.1)"
    )
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    args = parser.parse_args()

    port = args.port
    if port is None:
        if is_port_in_use(8000, args.host):
            print("Notice: Port 8000 is currently occupied by another process.")
            print("Switching ActionDesk backend to port 8001...")
            port = 8001
        else:
            port = 8000

    db_file = Path("memory.db")
    if not db_file.exists():
        print("Initializing and seeding sample business data into memory.db...")
        seed_database(db_file)
        print("Database seeded successfully.")

    print("\nStarting ActionDesk Business Memory Backend API:")
    print(f"  URL:      http://{args.host}:{port}")
    print(f"  Swagger:  http://{args.host}:{port}/docs")
    print(f"  ReDoc:    http://{args.host}:{port}/redoc")
    print(f"  Entities: http://{args.host}:{port}/api/entities")
    if port != 8000:
        print(f"  Frontend env: Set NEXT_PUBLIC_API_URL=http://{args.host}:{port}")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run("memory.api:app", host=args.host, port=port, reload=not args.no_reload)


if __name__ == "__main__":
    main()
