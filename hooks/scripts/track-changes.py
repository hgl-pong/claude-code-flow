#!/usr/bin/env python
"""PostToolUse(Write|Edit): track modified files for review pipeline with ownership."""
import json, os, sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
OWNERSHIP_FILE = os.path.join(FLOW_DIR, "modified-files.jsonl")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    os.makedirs(FLOW_DIR, exist_ok=True)
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        return

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        return

    # Normalize to relative path
    try:
        rel = os.path.relpath(file_path)
    except ValueError:
        rel = file_path

    # Determine action: created or modified
    action = "modified" if os.path.exists(file_path) else "created"

    # Determine agent from session state
    agent = "main"
    state_file = os.path.join(FLOW_DIR, "workflow-state.json")
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                current_agent = state.get("current_agent")
                if current_agent:
                    agent = current_agent
        except (json.JSONDecodeError, Exception):
            pass

    # Append to JSONL ownership log
    entry = {
        "file": rel,
        "action": action,
        "agent": agent,
        "ts": now(),
    }
    with open(OWNERSHIP_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    main()
