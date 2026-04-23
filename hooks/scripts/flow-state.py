#!/usr/bin/env python
"""Manage workflow state file. Usage: flow-state.py <action> [args]"""
import json, os, sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")

def default_state():
    return {"phase": "idle", "task_done": 0, "task_total": 0, "updated_at": ""}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default_state()
    return default_state()

def save_state(state):
    os.makedirs(FLOW_DIR, exist_ok=True)
    state["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""

    if action == "set-phase":
        phase = sys.argv[2] if len(sys.argv) > 2 else "idle"
        state = load_state()
        state["phase"] = phase
        save_state(state)

    elif action == "set-tasks":
        done = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        total = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        state = load_state()
        state["task_done"] = done
        state["task_total"] = total
        save_state(state)

    elif action == "clear":
        os.makedirs(FLOW_DIR, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(default_state(), f)
        for fname in ["modified-files.txt", "review-result.txt"]:
            fpath = os.path.join(FLOW_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
