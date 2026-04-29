#!/usr/bin/env python
"""PostToolUse(Bash): record verification evidence from test/build/lint commands."""
import json
import os
import re
import sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")
EVIDENCE_FILE = os.path.join(FLOW_DIR, "verification-evidence.jsonl")
LAST_FILE = os.path.join(FLOW_DIR, "last-verification.json")
EXEC_LOG = os.path.join(FLOW_DIR, "exec-log.jsonl")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")

PATTERNS = [
    ("test", re.compile(r"\b(pytest|vitest|jest|mocha|go\s+test|cargo\s+test|npm\s+(run\s+)?test|pnpm\s+(run\s+)?test|yarn\s+test|mvn\s+test|gradle\s+test)\b", re.I)),
    ("build", re.compile(r"\b(npm\s+run\s+build|pnpm\s+(run\s+)?build|yarn\s+build|cargo\s+build|go\s+build|mvn\s+package|gradle\s+build|make(\s|$))\b", re.I)),
    ("lint", re.compile(r"\b(eslint|ruff|flake8|pylint|golangci-lint|cargo\s+clippy|npm\s+(run\s+)?lint|pnpm\s+(run\s+)?lint|yarn\s+lint)\b", re.I)),
    ("typecheck", re.compile(r"\b(tsc|mypy|pyright|npm\s+(run\s+)?typecheck|pnpm\s+(run\s+)?typecheck|yarn\s+typecheck)\b", re.I)),
    ("git", re.compile(r"\bgit\s+(status|diff|show|log)\b", re.I)),
    ("dev-server", re.compile(r"\b(npm\s+run\s+dev|pnpm\s+(run\s+)?dev|yarn\s+dev|vite|next\s+dev)\b", re.I)),
]


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_session_id():
    if os.path.exists(SESSION_ID_FILE):
        with open(SESSION_ID_FILE, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    return "unknown"


def extract_command(data):
    tool_input = data.get("tool_input", {})
    if isinstance(tool_input, dict):
        return tool_input.get("command", "") or tool_input.get("cmd", "")
    if isinstance(tool_input, str):
        return tool_input
    return data.get("command", "")


def extract_exit_code(data):
    candidates = [
        data.get("exit_code"),
        data.get("exitCode"),
        data.get("status"),
    ]
    for key in ("tool_response", "tool_result", "result"):
        value = data.get(key, {})
        if isinstance(value, dict):
            candidates.extend([value.get("exit_code"), value.get("exitCode"), value.get("status")])

    for value in candidates:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().lstrip("-").isdigit():
            return int(value)
    return None


def classify(command):
    matches = []
    for kind, pattern in PATTERNS:
        if pattern.search(command):
            matches.append(kind)
    return matches


def status_from_exit(exit_code):
    if exit_code is None:
        return "unknown"
    return "pass" if exit_code == 0 else "fail"


def update_state(entry):
    state = {
        "session_id": get_session_id(),
        "phase": "idle",
        "task_done": 0,
        "task_total": 0,
        "updated_at": "",
        "created_at": entry["ts"],
        "mode": "standard",
        "current_agent": None,
        "phase_history": [],
        "plan_hash": None,
        "retry_count": 0,
        "verification_count": 0,
        "last_verification": None,
    }
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    state.update(loaded)
        except (json.JSONDecodeError, Exception):
            pass

    state["verification_count"] = int(state.get("verification_count", 0)) + 1
    state["last_verification"] = {
        "ts": entry["ts"],
        "kind": entry["kind"],
        "status": entry["status"],
        "command": entry["command"],
    }
    state["updated_at"] = entry["ts"]

    os.makedirs(FLOW_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def main():
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        return

    command = extract_command(data).strip()
    if not command:
        return

    kinds = classify(command)
    if not kinds:
        return

    ts = now()
    exit_code = extract_exit_code(data)
    status = status_from_exit(exit_code)
    entry = {
        "ts": ts,
        "session_id": get_session_id(),
        "event": "verification_evidence",
        "kind": kinds,
        "status": status,
        "exit_code": exit_code,
        "command": command,
    }

    os.makedirs(FLOW_DIR, exist_ok=True)
    with open(EVIDENCE_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        json.dump(entry, f, indent=2)
    with open(EXEC_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    update_state(entry)


if __name__ == "__main__":
    main()
