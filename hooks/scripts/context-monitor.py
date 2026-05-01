#!/usr/bin/env python
"""PreToolUse: monitor tool call frequency and suggest preemptive compaction."""
import json, os, sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
COUNT_FILE = os.path.join(FLOW_DIR, "tool-call-count.txt")
LAST_ALERT_FILE = os.path.join(FLOW_DIR, "context-alert.txt")

DEFAULT_THRESHOLD = int(os.environ.get("CLAUDE_CONTEXT_MONITOR_THRESHOLD", "50"))

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    os.makedirs(FLOW_DIR, exist_ok=True)

    count = 0
    if os.path.exists(COUNT_FILE):
        try:
            with open(COUNT_FILE, "r") as f:
                count = int(f.read().strip())
        except (ValueError, Exception):
            count = 0

    count += 1
    with open(COUNT_FILE, "w") as f:
        f.write(str(count))

    if count < DEFAULT_THRESHOLD:
        return

    # Already alerted at this threshold cycle?
    last_alert = ""
    if os.path.exists(LAST_ALERT_FILE):
        try:
            with open(LAST_ALERT_FILE, "r") as f:
                last_alert = f.read().strip()
        except Exception:
            pass

    alert_key = f"alert-{count // DEFAULT_THRESHOLD}"
    if last_alert == alert_key:
        return

    with open(LAST_ALERT_FILE, "w") as f:
        f.write(alert_key)

    # Log the alert
    entry = {
        "ts": now(),
        "event": "context_health_check",
        "tool_call_count": count,
        "threshold": DEFAULT_THRESHOLD,
        "action": "preemptive_compaction_suggested",
    }
    log_file = os.path.join(FLOW_DIR, "exec-log.jsonl")
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    # Block with suggestion
    output = {
        "decision": "block",
        "reason": "context health check",
        "systemMessage": (
            f"[Context Monitor] {count} tool calls in this session. "
            "Context window may be getting large. Consider using /compact or "
            "narrowing focus to the current task scope before continuing."
        ),
    }
    print(json.dumps(output))

if __name__ == "__main__":
    main()
