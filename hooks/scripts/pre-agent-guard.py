#!/usr/bin/env python
"""PreToolUse(agent): validate sentinel has a concrete review target."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path


FLOW_DIR = Path(".claude") / "flow"
MODIFIED_FILES = FLOW_DIR / "modified-files.jsonl"
LOG_EVENT_SCRIPT = Path(__file__).with_name("log-event.py")

REVIEW_TARGET_RE = re.compile(
    r"review_focus|document_quality|spec_compliance|code_quality|Files to review|"
    r"File Scope|diff summary|target files|relevant diff|--docs|--diff|"
    r"\.claude/flow|([A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]*|"
    r"[A-Za-z0-9_./-]+\.(py|js|ts|tsx|jsx|md|json|ya?ml|sh|toml|css|scss|"
    r"html|go|rs|java|kt|cs|cpp|c|h|hpp|txt|diff|patch)",
    re.IGNORECASE,
)


def has_flow_modified_files():
    return MODIFIED_FILES.exists() and MODIFIED_FILES.stat().st_size > 0


def has_git_changes():
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return False
    return bool(result.stdout.strip())


def log_block():
    try:
        subprocess.run(
            [
                sys.executable,
                str(LOG_EVENT_SCRIPT),
                "tool_guard_block",
                "guard=pre-agent",
                "agent=sentinel",
                "reason=no_review_target",
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        pass


def main():
    raw = sys.stdin.read()
    if "sentinel" not in raw.lower():
        return

    if has_flow_modified_files() or has_git_changes() or REVIEW_TARGET_RE.search(raw):
        return

    log_block()
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": (
                    "No review target found. Provide files, diff/context, "
                    "document review_focus, or run implementation first."
                ),
            }
        ),
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
