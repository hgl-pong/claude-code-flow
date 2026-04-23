#!/usr/bin/env python
"""SubagentStop: log agent completion timestamp."""
import json, os, sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
LOG_FILE = os.path.join(FLOW_DIR, "agent-log.txt")

def main():
    os.makedirs(FLOW_DIR, exist_ok=True)
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        return

    agent_name = data.get("name", "")
    if not agent_name:
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {agent_name} completed\n")

if __name__ == "__main__":
    main()
