#!/usr/bin/env python
"""PreToolUse(shell): block git commit when workflow changes are unreviewed."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


FLOW_DIR = Path(".claude") / "flow"
TRACK_FILE = FLOW_DIR / "modified-files.jsonl"
LOG_EVENT_SCRIPT = Path(__file__).with_name("log-event.py")


def extract_command(payload):
    tool_input = payload.get("tool_input", {})
    if isinstance(tool_input, dict):
        return tool_input.get("command", "") or tool_input.get("cmd", "")
    if isinstance(tool_input, str):
        return tool_input
    return payload.get("command", "")


def log_block(count):
    try:
        subprocess.run(
            [
                sys.executable,
                str(LOG_EVENT_SCRIPT),
                "tool_guard_block",
                "guard=pre-commit",
                f"file_count={count}",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return

    command = extract_command(payload)
    if not re.search(r"\bgit\s+commit\b", command):
        return

    if TRACK_FILE.exists() and TRACK_FILE.stat().st_size > 0:
        count = len(TRACK_FILE.read_text(encoding="utf-8", errors="ignore").splitlines())
        log_block(count)
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": (
                        f"You have {count} unreviewed modified file(s). "
                        "Consider running /workflow-review first."
                    ),
                }
            ),
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
