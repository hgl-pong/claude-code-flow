#!/usr/bin/env python
"""PostCompact: verify workflow state consistency after context compaction."""
import json, os
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")
TASK_GRAPH = os.path.join(FLOW_DIR, "task-graph.json")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except (json.JSONDecodeError, Exception):
            pass

    phase = state.get("phase", "unknown")
    mode = state.get("mode", "standard")
    task_done = state.get("task_done", 0)
    task_total = state.get("task_total", 0)
    retry = state.get("retry_count", 0)

    warnings = []

    # Check for running tasks in task-graph that may have been interrupted
    if os.path.exists(TASK_GRAPH):
        try:
            with open(TASK_GRAPH, "r") as f:
                graph = json.load(f)
            running = [n for n in graph.get("nodes", []) if n.get("status") == "running"]
            if running:
                names = ", ".join(n["title"] for n in running[:3])
                warnings.append(f"running tasks may be interrupted: {names}")
        except (json.JSONDecodeError, Exception):
            pass

    # Output recovery context to stdout (included in post-compact context)
    print(f"FLOW: Post-compact recovery at {now()}")
    print(f"FLOW: Phase={phase}, Tasks={task_done}/{task_total}, Mode={mode}, Retries={retry}")

    if warnings:
        for w in warnings:
            print(f"FLOW: WARNING: {w}")

    if phase not in ("idle", "unknown"):
        print(f"FLOW: Resume pipeline from '{phase}' phase. Re-read phase-context.md for context.")

if __name__ == "__main__":
    main()
