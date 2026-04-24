#!/usr/bin/env python
"""Stop: persist workflow state summary with structured logging."""
import json, os
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
SUMMARY_FILE = os.path.join(FLOW_DIR, "session-summary.txt")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")
MODIFIED_FILE = os.path.join(FLOW_DIR, "modified-files.txt")
EXEC_LOG = os.path.join(FLOW_DIR, "exec-log.jsonl")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")

def get_session_id():
    if os.path.exists(SESSION_ID_FILE):
        with open(SESSION_ID_FILE, "r") as f:
            return f.read().strip()
    return "unknown"

def main():
    os.makedirs(FLOW_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    phase = "unknown"
    task_done = 0
    task_total = 0
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                phase = state.get("phase", "unknown")
                task_done = state.get("task_done", 0)
                task_total = state.get("task_total", 0)
        except (json.JSONDecodeError, Exception):
            pass

    modified = 0
    if os.path.exists(MODIFIED_FILE):
        with open(MODIFIED_FILE, "r") as f:
            modified = sum(1 for line in f if line.strip())

    # Legacy summary (backward compatible)
    with open(SUMMARY_FILE, "a") as f:
        f.write(f"[{ts}] phase={phase} | modified={modified}\n")

    # Structured JSONL log
    entry = {
        "ts": ts,
        "session_id": get_session_id(),
        "event": "workflow_stop",
        "phase": phase,
        "task_done": task_done,
        "task_total": task_total,
        "modified_files": modified,
    }
    with open(EXEC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    main()
