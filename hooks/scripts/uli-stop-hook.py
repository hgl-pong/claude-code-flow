#!/usr/bin/env python
"""Portable ULI Stop hook for hosts without bash+jq."""

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

FLOW_DIR = Path(".claude") / "flow"
STATE_FILE = FLOW_DIR / "uli-state.json"
STUCK_FILE = FLOW_DIR / "uli" / "stuck-tracker.json"
PRODUCT_STATE_FILE = FLOW_DIR / "uli" / "product-state.md"


def phase_message(phase, iteration, slug):
    slug_hint = slug or "<slug>"
    if phase == "pd_generating":
        return (
            "Product analysis + proposal must run for this iteration. Continue: "
            "spawn research subagent to analyze product state, then oracle to propose "
            f"requirements, wait for uli/{slug_hint}/proposal.md with at least 1 CORE "
            "requirement, then proceed to oracle plan."
        )
    if phase == "dev_pipeline":
        return (
            f"The dev pipeline is still in progress for iteration {iteration}. Continue: "
            "complete ALL implementation tasks for this iteration, run sentinel review "
            "(two-stage), then run prism acceptance. Do NOT advance to next iteration "
            "until acceptance passes."
        )
    if phase == "acceptance":
        return (
            f"Acceptance gate is pending for iteration {iteration}. Continue: run prism "
            f"for acceptance, check build + tests + feature checklist against uli/{slug_hint}/"
            "proposal.md, record result. Only on ACCEPT: commit, update uli/product-state.md, "
            "increment iteration via uli-next, then spawn PD for next iteration."
        )
    return (
        f"Continue the ULI iteration loop for iteration {iteration}: PD proposal exists -> "
        "implement ALL tasks -> sentinel review -> hard acceptance -> commit -> increment -> "
        "PD for next iteration."
    )


def product_state_summary():
    try:
        summary = PRODUCT_STATE_FILE.read_text(encoding="utf-8", errors="ignore")[:500]
    except OSError:
        return ""
    collapsed = " ".join(summary.splitlines()[:3]).strip()
    return f" | Product state: {collapsed}" if collapsed else ""


def main():
    hook_input = read_hook_input()
    state = load_active_state(STATE_FILE)
    if not state:
        return

    if not session_matches(state, hook_input):
        return

    iteration = int(state.get("iteration", 1) or 1)
    max_iterations = int(state.get("max_iterations", 10) or 10)
    if max_iterations > 0 and iteration > max_iterations:
        print(f"ULI: Max iterations ({max_iterations}) reached. Stopping.")
        mark_inactive(STATE_FILE, state)
        return

    transcript_path = hook_input.get("transcript_path") or ""
    last_output = last_assistant_text(transcript_path)
    if last_output is None:
        print("WARNING: ULI: Transcript not found, stopping.", file=sys.stderr)
        mark_inactive(STATE_FILE, state)
        return

    summary = completion_summary(last_output, "uli-done")
    if summary:
        print(f"ULI: All iterations complete - {summary}")
        mark_inactive(STATE_FILE, state)
        return

    phase = state.get("current_phase") or "pd_generating"
    goal = state.get("goal") or "continue product development"
    slug = state.get("current_task_slug") or ""

    stuck = load_json(STUCK_FILE, {"current_phase": "", "stuck_count": 0})
    if phase == stuck.get("current_phase") and phase != "complete":
        stuck_count = int(stuck.get("stuck_count", 0) or 0) + 1
    else:
        stuck_count = 0
    save_json(STUCK_FILE, {"current_phase": phase, "stuck_count": stuck_count})

    stuck_msg = ""
    if stuck_count >= 3:
        stuck_msg = (
            f" WARNING: Stuck in '{phase}' phase for {stuck_count} iterations. "
            "Consider escalating or adjusting the approach. Do NOT emit <uli-done> "
            "unless the product goal is fully delivered."
        )

    system_message = (
        f"ULI iteration {iteration}/{max_iterations} | goal: {goal} | phase: {phase} | "
        f"{phase_message(phase, iteration, slug)}{product_state_summary()}{stuck_msg} | "
        "Output <uli-done>SUMMARY</uli-done> ONLY when all iterations are complete "
        "or the product goal is fully delivered."
    )
    continuation_prompt = (
        f"Continue ULI iteration {iteration}. Goal: {goal}. Phase: {phase}."
        f"{f' Task slug: {slug}.' if slug else ''} ONE ITERATION = one PD proposal + "
        "all tasks delivered + acceptance passed + commit. Do NOT treat individual tasks "
        "as iterations. Read .claude/flow/uli-state.json and .claude/flow/uli/"
        f"{slug or '<slug>'}/ to understand where to resume, then continue the ultrawork "
        "skill ULI branch."
    )
    print(
        json.dumps(
            {
                "decision": "block",
                "reason": continuation_prompt,
                "systemMessage": system_message,
            }
        )
    )


if __name__ == "__main__":
    main()
