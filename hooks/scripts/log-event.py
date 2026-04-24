#!/usr/bin/env python
"""Unified event logger for all workflow hooks. Usage: log-event.py <event_type> [key=value ...]"""
import json, os, sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
LOG_FILE = os.path.join(FLOW_DIR, "exec-log.jsonl")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")

VALID_EVENTS = [
    "phase_transition", "agent_start", "agent_complete",
    "tool_guard_block", "review_result", "error",
    "workflow_stop", "session_start", "session_end",
]

def get_session_id():
    if os.path.exists(SESSION_ID_FILE):
        with open(SESSION_ID_FILE, "r") as f:
            return f.read().strip()
    return "unknown"

def main():
    event_type = sys.argv[1] if len(sys.argv) > 1 else ""
    if event_type not in VALID_EVENTS:
        print(f"Invalid event type: {event_type}", file=sys.stderr)
        sys.exit(1)

    entry = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_id": get_session_id(),
        "event": event_type,
    }

    # Parse key=value pairs from remaining args
    for arg in sys.argv[2:]:
        if "=" in arg:
            key, value = arg.split("=", 1)
            entry[key] = value

    os.makedirs(FLOW_DIR, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    main()
