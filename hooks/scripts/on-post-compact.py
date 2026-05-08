#!/usr/bin/env python
"""PostCompact: verify workflow state consistency after context compaction."""
import json, os
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except (json.JSONDecodeError, Exception):
            pass

    phase = state.get("phase", "unknown")
    mode = state.get("mode", "standard")
    task_done = state.get("task_done", 0)
    task_total = state.get("task_total", 0)
    retry = state.get("retry_count", 0)

    warnings = []

    # Output recovery context to stdout (included in post-compact context)
    print(f"FLOW: Post-compact recovery at {now()}")
    print(f"FLOW: Phase={phase}, Tasks={task_done}/{task_total}, Mode={mode}, Retries={retry}")

    if warnings:
        for w in warnings:
            print(f"FLOW: WARNING: {w}")

    if phase not in ("idle", "unknown"):
        print(f"FLOW: Resume pipeline from '{phase}' phase. Re-read phase-context.md for context.")

if __name__ == "__main__":
    main()
