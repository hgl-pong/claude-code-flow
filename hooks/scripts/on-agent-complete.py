#!/usr/bin/env python
"""SubagentStop: log agent completion with structured data."""
import json, os, re, sys
from datetime import datetime, timezone
from pathlib import Path

FLOW_DIR = os.path.join(".claude", "flow")
EXEC_LOG = os.path.join(FLOW_DIR, "exec-log.jsonl")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")

def agent_models():
    models = {}
    agents_dir = Path(__file__).resolve().parents[2] / "agents"
    for path in agents_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
        if not match:
            continue
        fields = {}
        for line in match.group(1).splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip('"')
        name = fields.get("name")
        model = fields.get("model")
        if name and model:
            models[name] = model
    return models

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

    # Structured JSONL log
    entry = {
        "ts": ts,
        "session_id": get_session_id(),
        "event": "agent_complete",
        "agent": agent_name,
        "model": agent_models().get(agent_name, "unknown"),
        "status": "success",
        "phase": get_phase(),
    }
    with open(EXEC_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

if __name__ == "__main__":
    main()
