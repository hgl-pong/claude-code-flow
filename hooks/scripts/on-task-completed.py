#!/usr/bin/env python
"""TaskCompleted: log task completion and auto-update flow-state counters."""
import json, os, sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
EXEC_LOG = os.path.join(FLOW_DIR, "exec-log.jsonl")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")

def get_session_id():
    if os.path.exists(SESSION_ID_FILE):
        with open(SESSION_ID_FILE, "r") as f:
            return f.read().strip()
    return "unknown"

def get_phase():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f).get("phase", "unknown")
        except (json.JSONDecodeError, Exception):
            pass
    return "unknown"

def main():
    os.makedirs(FLOW_DIR, exist_ok=True)
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    entry = {
        "ts": ts,
        "session_id": get_session_id(),
        "event": "task_completed",
        "task_id": data.get("task_id", ""),
        "task_subject": data.get("task_subject", ""),
        "owner": data.get("teammate_name", ""),
        "phase": get_phase(),
    }
    with open(EXEC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Auto-update flow-state task counters
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            done = state.get("task_done", 0) + 1
            state["task_done"] = done
            # Ensure task_total is at least as large as task_done
            if state.get("task_total", 0) < done:
                state["task_total"] = done
            state["updated_at"] = ts
            with open(STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except (json.JSONDecodeError, Exception):
            pass

if __name__ == "__main__":
    main()
