#!/usr/bin/env python
"""SubagentStop: log agent completion with structured data."""
import json, os, sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
LOG_FILE = os.path.join(FLOW_DIR, "agent-log.txt")
EXEC_LOG = os.path.join(FLOW_DIR, "exec-log.jsonl")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")

AGENT_MODELS = {
    "oracle": "opus", "atlas": "opus", "forge": "sonnet",
    "prism": "sonnet", "anvil": "haiku", "sentinel": "sonnet",
    "chronicler": "sonnet", "scout": "sonnet", "evolver": "opus",
}

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

    agent_name = data.get("name", "")
    if not agent_name:
        return

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Legacy log (backward compatible)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}] {agent_name} completed\n")

    # Structured JSONL log
    entry = {
        "ts": ts,
        "session_id": get_session_id(),
        "event": "agent_complete",
        "agent": agent_name,
        "model": AGENT_MODELS.get(agent_name, "unknown"),
        "status": "success",
        "phase": get_phase(),
    }
    with open(EXEC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    main()
