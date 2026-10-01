"""Layer 1 build agent via the Claude API, with the harness enforced in code.

Setup:  pip install anthropic
        export ANTHROPIC_API_KEY=...
Run:    python layer1_agent.py

The agent works only inside ./workspace. It can read/write files and call
run_verify. Your code, not the model, decides when the job is done.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import anthropic

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-7-sonnet-latest")
WORKDIR = Path("workspace").resolve()
MAX_TURNS = 60  # hard cap on the whole session
MAX_VERIFY_FAILS = 3  # stop and report after this many failed verifies in a row
BLOCKED_NAMES = {"credentials.json", "token.json", ".env"}

PROMPT_FILE = Path("layer1_prompt.md")
SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8") if PROMPT_FILE.exists() else ""

TOOLS = [
    {
        "name": "write_file",
        "description": "Create or overwrite a file inside the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file inside the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "run_verify",
        "description": "Run `make verify` in the workspace and return its output.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def safe_path(rel: str) -> Path:
    p = (WORKDIR / rel).resolve()
    if WORKDIR not in p.parents and p != WORKDIR:
        raise ValueError("Path escapes workspace")
    if p.name in BLOCKED_NAMES:
        raise ValueError(f"Writing/reading {p.name} is not allowed")
    return p


def run_verify() -> tuple[bool, str]:
    if shutil.which("make"):
        r = subprocess.run(
            ["make", "verify"],  # noqa: S603, S607
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return r.returncode == 0, (r.stdout + r.stderr)[-6000:]

    # Cross-platform fallback when `make` is not available
    steps = [
        [sys.executable, "-m", "ruff", "check", "actiondesk/", "connectors/", "tests/"],
        [sys.executable, "-m", "mypy", "actiondesk/", "connectors/", "--ignore-missing-imports"],
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    ]
    combined_output: list[str] = []
    for step in steps:
        r = subprocess.run(  # noqa: S603
            step, cwd=WORKDIR, capture_output=True, text=True, timeout=300
        )
        combined_output.append(r.stdout + r.stderr)
        if r.returncode != 0:
            return False, "\n".join(combined_output)[-6000:]
    return True, "\n".join(combined_output)[-6000:]


def handle_tool(name: str, args: dict[str, Any]) -> tuple[str, bool | None]:
    """Returns (result_text, verify_passed_or_None)."""
    try:
        if name == "write_file":
            p = safe_path(args["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(args["content"], encoding="utf-8")
            return f"Wrote {args['path']}", None
        if name == "read_file":
            return safe_path(args["path"]).read_text(encoding="utf-8")[:20000], None
        if name == "run_verify":
            ok, out = run_verify()
            return ("PASS\n" if ok else "FAIL\n") + out, ok
    except Exception as e:  # report errors to the model instead of crashing
        return f"ERROR: {e}", None
    return "Unknown tool", None


def main() -> None:
    WORKDIR.mkdir(exist_ok=True)
    client = anthropic.Anthropic()
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": "Begin. Start with the harness and fixtures."}
    ]
    verify_fails = 0

    for _turn in range(MAX_TURNS):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,  # type: ignore[arg-type]
            messages=messages,  # type: ignore[arg-type]
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "tool_use":
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    text, ok = handle_tool(block.name, block.input)  # type: ignore[arg-type]
                    if ok is not None:
                        verify_fails = 0 if ok else verify_fails + 1
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": text}
                    )
            messages.append({"role": "user", "content": results})
            if verify_fails >= MAX_VERIFY_FAILS:
                print("STOPPED: verify failed 3 times in a row. Review workspace/PROGRESS.md.")
                return
            continue

        # Model thinks it is finished. The gate is checked by code, not by the model.
        ok, out = run_verify()
        if ok:
            print("DONE: make verify passes.")
            print("".join(getattr(b, "text", "") for b in resp.content))
            return
        messages.append({
            "role": "user",
            "content": f"Not done. make verify fails:\n{out}\nFix it and continue.",
        })

    print("STOPPED: hit MAX_TURNS without passing verify.")


if __name__ == "__main__":
    main()
