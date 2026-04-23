#!/usr/bin/env python
"""Stop: persist workflow state summary."""
import json, os
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
SUMMARY_FILE = os.path.join(FLOW_DIR, "session-summary.txt")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")
MODIFIED_FILE = os.path.join(FLOW_DIR, "modified-files.txt")

def main():
    os.makedirs(FLOW_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    phase = "unknown"
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                phase = json.load(f).get("phase", "unknown")
        except (json.JSONDecodeError, Exception):
            pass

    modified = 0
    if os.path.exists(MODIFIED_FILE):
        with open(MODIFIED_FILE, "r") as f:
            modified = sum(1 for line in f if line.strip())

    with open(SUMMARY_FILE, "a") as f:
        f.write(f"[{ts}] phase={phase} | modified={modified}\n")

if __name__ == "__main__":
    main()
