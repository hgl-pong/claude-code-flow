#!/usr/bin/env python
"""Portable ULW Stop hook for hosts without bash+jq."""

import json
import sys
from pathlib import Path

from stop_hook_common import (
    completion_summary,
    last_assistant_text,
    load_active_state,
    load_json,
    mark_inactive,
    read_hook_input,
    save_json,
    session_matches,
)

STATE_FILE = Path(".claude") / "flow" / "ulw-state.json"
STUCK_FILE = Path(".claude") / "flow" / "ulw-stuck-tracker.json"


def main():
    hook_input = read_hook_input()
    state = load_active_state(STATE_FILE)
    if not state:
        return

    if not session_matches(state, hook_input):
        return

    iteration = int(state.get("iteration", 0) or 0)
    max_iterations = int(state.get("max_iterations", 25) or 25)
    if max_iterations > 0 and iteration >= max_iterations:
        print(f"ULW: Max iterations ({max_iterations}) reached. Stopping.")
        mark_inactive(STATE_FILE, state)
        return

    transcript_path = hook_input.get("transcript_path") or ""
    last_output = last_assistant_text(transcript_path)
    if last_output is None:
        print("WARNING: ULW: Transcript not found, stopping.", file=sys.stderr)
        mark_inactive(STATE_FILE, state)
        return

    summary = completion_summary(last_output, "ulw-done")
    if summary:
        print(f"ULW: Task complete - {summary}")
        mark_inactive(STATE_FILE, state)
        return

    prompt = state.get("prompt") or ""
    if not prompt:
        print("WARNING: ULW: No prompt in state file, stopping.", file=sys.stderr)
        mark_inactive(STATE_FILE, state)
        return

    task_done = int(state.get("task_done", 0) or 0)
    task_total = int(state.get("task_total", 0) or 0)
    next_iteration = iteration + 1
    state["iteration"] = next_iteration
    save_json(STATE_FILE, state)

    stuck_msg = ""
    if task_total > 0:
        stuck = load_json(STUCK_FILE, {"task_done": 0, "stuck_count": 0})
        stuck_count = int(stuck.get("stuck_count", 0) or 0)
        if task_done == int(stuck.get("task_done", 0) or 0) and task_done < task_total:
            stuck_count += 1
        else:
            stuck_count = 0
        save_json(STUCK_FILE, {"task_done": task_done, "stuck_count": stuck_count})
        if stuck_count >= 3:
            stuck_msg = (
                f" WARNING: Task progress has stalled for {stuck_count} iterations. "
                "Consider breaking down the current task or escalating. Do NOT emit "
                "<ulw-done> until tasks are complete."
            )

    progress = f"{task_done}/{task_total} tasks done" if task_total > 0 else "tasks in progress"
    system_message = (
        f"ULW iteration {next_iteration} | intent:{state.get('intent') or 'implement'} | "
        f"{progress} | Keep working until ALL tasks have fresh verification evidence. "
        "Output <ulw-done>SUMMARY</ulw-done> ONLY when everything is verified complete."
        f"{stuck_msg}"
    )
    print(json.dumps({"decision": "block", "reason": prompt, "systemMessage": system_message}))


if __name__ == "__main__":
    main()
