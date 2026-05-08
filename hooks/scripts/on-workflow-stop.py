#!/usr/bin/env python
"""Stop: persist workflow state summary with structured logging."""
import json, os
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")
LAST_VERIFICATION = os.path.join(FLOW_DIR, "last-verification.json")
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

    last_verification = None
    if os.path.exists(LAST_VERIFICATION):
        try:
            with open(LAST_VERIFICATION, "r", encoding="utf-8") as f:
                last_verification = json.load(f)
        except (json.JSONDecodeError, Exception):
            last_verification = None

    # Structured JSONL log
    entry = {
        "ts": ts,
        "session_id": get_session_id(),
        "event": "workflow_stop",
        "phase": phase,
        "task_done": task_done,
        "task_total": task_total,
        "modified_files": 0,
        "last_verification": last_verification,
    }
    with open(EXEC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    main()
