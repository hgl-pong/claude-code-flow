#!/usr/bin/env python
"""PreCompact: preserve workflow state before context compaction."""
import json, os
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")
PHASE_CONTEXT = os.path.join(FLOW_DIR, "phase-context.md")
TASK_GRAPH = os.path.join(FLOW_DIR, "task-graph.json")
PRE_COMPACT = os.path.join(FLOW_DIR, "pre-compact-context.md")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    os.makedirs(FLOW_DIR, exist_ok=True)
    sections = []

    # 1. Current state
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except (json.JSONDecodeError, Exception):
            pass

    sections.append(f"# Pre-Compact Context ({now()})\n")
    sections.append("## Current State")
    sections.append(f"- Phase: {state.get('phase', 'unknown')}")
    sections.append(f"- Mode: {state.get('mode', 'standard')}")
    sections.append(f"- Tasks: {state.get('task_done', 0)}/{state.get('task_total', 0)}")
    sections.append(f"- Retry count: {state.get('retry_count', 0)}")
    sections.append("")

    # 2. Task graph summary
    if os.path.exists(TASK_GRAPH):
        try:
            with open(TASK_GRAPH, "r") as f:
                graph = json.load(f)
            if graph.get("nodes"):
                sections.append("## Task Graph")
                for n in graph["nodes"]:
                    deps = n.get("dependencies", [])
                    dep_str = f" (after: {', '.join(deps)})" if deps else ""
                    sections.append(f"- [{n['status']}] {n['id']}: {n['title']} ({n['agent']}){dep_str}")
                sections.append("")
        except (json.JSONDecodeError, Exception):
            pass

    # 3. Key decisions from phase-context (last 30 lines if file is large)
    if os.path.exists(PHASE_CONTEXT):
        try:
            with open(PHASE_CONTEXT, "r") as f:
                lines = f.readlines()
            if lines:
                sections.append("## Phase Context (recent)")
                for line in lines[-30:]:
                    sections.append(line.rstrip())
                sections.append("")
        except Exception:
            pass

    content = "\n".join(sections)
    with open(PRE_COMPACT, "w") as f:
        f.write(content)

    print(f"FLOW: Pre-compact context saved to {PRE_COMPACT}")

if __name__ == "__main__":
    main()
