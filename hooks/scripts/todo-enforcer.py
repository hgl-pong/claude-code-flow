#!/usr/bin/env python
"""Stop: enforce task completion before allowing exit in ULI mode."""
import json, os, sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
ULI_STATE = os.path.join(FLOW_DIR, "uli-state.json")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get_remaining_tasks():
    """Read task state from workflow-state.json to find pending tasks."""
    state_file = os.path.join(FLOW_DIR, "workflow-state.json")
    if not os.path.exists(state_file):
        return []

    try:
        with open(state_file, "r") as f:
            state = json.load(f)
    except (json.JSONDecodeError, Exception):
        return []

    task_done = state.get("task_done", 0)
    task_total = state.get("task_total", 0)
    remaining = task_total - task_done
    if remaining <= 0:
        return []

    return [f"{task_done}/{task_total} tasks completed, {remaining} remaining"]

def main():
    os.makedirs(FLOW_DIR, exist_ok=True)

    active_mode = None

    if os.path.exists(ULI_STATE):
        try:
            with open(ULI_STATE, "r") as f:
                uli = json.load(f)
            if uli.get("active"):
                active_mode = "uli"
        except (json.JSONDecodeError, Exception):
            pass

    if not active_mode:
        return

    # Check transcript for completion tag
    try:
        data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, Exception):
        return

    transcript = data.get("transcript_path", "")
    done_tag = "<uli-done>"

    if transcript and os.path.exists(transcript):
        try:
            with open(transcript, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if done_tag in content:
                return  # Completion detected, allow exit
        except Exception:
            pass

    # Get remaining task context
    remaining = get_remaining_tasks()
    task_info = " | ".join(remaining) if remaining else "Task progress unknown"

    # Block and provide context
    output = {
        "decision": "block",
        "reason": f"{active_mode.upper()} active with incomplete tasks",
        "systemMessage": (
            f"[Todo Enforcer] {active_mode.upper()} session is not complete. "
            f"{task_info}. Continue working on remaining tasks. "
            f"Output {done_tag}SUMMARY{done_tag.replace('<', '</')} when ALL tasks are verified."
        ),
    }

    # Log the enforcement
    entry = {
        "ts": now(),
        "event": "todo_enforcement",
        "mode": active_mode,
        "task_info": task_info,
    }
    log_file = os.path.join(FLOW_DIR, "exec-log.jsonl")
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    print(json.dumps(output))

if __name__ == "__main__":
    main()
