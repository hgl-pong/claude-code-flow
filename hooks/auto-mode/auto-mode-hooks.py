#!/usr/bin/env python3
"""Auto-mode hook helpers — state discovery and enforcement via flow-state.py.

Hooks never write state directly. All state mutations go through
hooks/scripts/flow-state.py. Hooks read state for decision-making and
call flow-state.py snapshot for persistence.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TERMINAL_STATUSES = frozenset(("DONE", "FAILED_FATAL", "CANCELLED"))
NONTERMINAL_ACTIVE = frozenset(("ACTIVE", "PAUSED_COMPACTING", "BLOCKED_ESCALATING"))

GAVE_UP_RE = re.compile(
    r"(cannot proceed|cannot complete|unable to complete|unable to proceed"
    r"|need more information|need you to clarify|I need you to"
    r"|please clarify|I give up|what should I do next)",
    re.IGNORECASE,
)

FLOW_STATE_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts", "flow-state.py",
)


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def read_state_files() -> list[str]:
    """Find all state.json files under .claude/auto/."""
    auto_dir = ".claude/auto"
    if not os.path.isdir(auto_dir):
        return []
    state_files = []
    for task_dir in os.listdir(auto_dir):
        sf = os.path.join(auto_dir, task_dir, "state.json")
        if os.path.isfile(sf):
            state_files.append(sf)
    return sorted(state_files)


def load_json(path: str) -> Optional[dict]:
    """Load and parse a JSON file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def auto_mode_active() -> Optional[str]:
    """Return the path to the most recently updated active state.json, or None."""
    latest_file = None
    latest_time = ""
    for sf in read_state_files():
        data = load_json(sf)
        if not data:
            continue
        status = data.get("status", "")
        if status in TERMINAL_STATUSES or status == "STOPPED_ASK_USER":
            continue
        updated = data.get("updated_at", "")
        if updated > latest_time:
            latest_time = updated
            latest_file = sf
    return latest_file


def discover_active_states() -> list[dict]:
    """Return all active (nonterminal) state summaries from .claude/auto/*/state.json.

    Each dict has keys: state_file, task_name, phase, status, updated_at.
    """
    results = []
    for sf in read_state_files():
        data = load_json(sf)
        if not data:
            continue
        status = data.get("status", "")
        if status in TERMINAL_STATUSES:
            continue
        results.append({
            "state_file": sf,
            "task_name": data.get("task_name", "unknown"),
            "phase": data.get("phase", "unknown"),
            "status": status,
            "updated_at": data.get("updated_at", ""),
            "workflow_run_id": data.get("workflow_run_id", ""),
        })
    # Sort by updated_at descending
    results.sort(key=lambda r: r["updated_at"], reverse=True)
    return results


def _call_flow_state(*args) -> Optional[dict]:
    """Call flow-state.py with given args. Returns parsed JSON or None."""
    if not os.path.isfile(FLOW_STATE_SCRIPT):
        return None
    try:
        result = subprocess.run(
            [sys.executable, FLOW_STATE_SCRIPT] + list(args),
            capture_output=True, text=True, timeout=10,
        )
        if result.stdout.strip():
            data = json.loads(result.stdout)
            return data
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return None


def _call_flow_state_resume(state_file: str) -> Optional[dict]:
    """Call flow-state.py resume to get enriched resume data."""
    result = _call_flow_state("resume", "--state-file", state_file)
    if result and result.get("ok"):
        return result
    return None


def _call_flow_state_snapshot(state_file: str, reason: str = "pre-compact") -> Optional[dict]:
    """Call flow-state.py snapshot. Returns parsed output or None."""
    return _call_flow_state("snapshot", "--state-file", state_file, "--reason", reason)


# ---------------------------------------------------------------------------
# State read helpers (no writes)
# ---------------------------------------------------------------------------


def generate_resume_prompt(state_file: str) -> str:
    """Generate a state-aware resume prompt for the Stop hook.

    Uses flow-state.py resume command when available for enriched data
    including stale artifact invalidation and result_replay information.
    Falls back to direct JSON parsing if flow-state.py is unavailable.
    """
    resume_data = _call_flow_state_resume(state_file)

    data = load_json(state_file)
    if not data:
        return "AUTO-MODE CONTINUATION: State file unreadable."

    task_name = data.get("task_name", "unknown")
    phase = data.get("phase", "unknown")
    step = data.get("current_step", "unknown")
    status = data.get("status", "unknown")
    progress = data.get("progress", {})
    tasks_total = progress.get("tasks_total", 0)
    tasks_completed = progress.get("tasks_passed", progress.get("tasks_completed", 0))

    runtime = data.get("runtime_verification", {})
    runtime_status = runtime.get("status", "unknown")
    smoke_status = runtime.get("smoke", "unknown")
    crash_detected = runtime.get("crash_detected", False)
    hang_detected = runtime.get("hang_detected", False)
    evidence_dir = runtime.get("evidence_dir", "")

    # Task states summary
    task_states = data.get("task_states", {})
    ts_summary = ", ".join(
        f"{k}={v.get('status', '?')}" for k, v in task_states.items()
        if isinstance(v, dict)
    ) or "none"

    # Active agents summary
    active_agents = data.get("active_agents", [])
    aa_summary = ", ".join(
        f"{a.get('task_id', '?')}({a.get('role', '?')})" for a in active_agents
    ) or "none"

    # Failing gates (supports both dict and list format)
    gate_states = data.get("gate_states", {})
    if isinstance(gate_states, list):
        failing = ", ".join(
            g.get("gate", g.get("name", "?")) for g in gate_states
            if isinstance(g, dict) and not g.get("passed", False)
        ) or "none"
    else:
        failing = ", ".join(
            k for k, v in gate_states.items() if not v.get("passed", False)
        ) or "none"

    # Resume enrichment from flow-state.py
    resume_section = ""
    if resume_data:
        entrypoint = resume_data.get("next_entrypoint", "")
        invalidated_tasks = resume_data.get("invalidated_tasks", {})
        result_replay = resume_data.get("result_replay", [])

        resume_section = f"""
Resume data from flow-state.py:
- Next entrypoint: {entrypoint}
- Result replay (skip these tasks): {', '.join(result_replay) or 'none'}
- Invalidated tasks: {', '.join(f'{k}: {v}' for k, v in invalidated_tasks.items()) or 'none'}
"""

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return f"""AUTO-MODE CONTINUATION — task: {task_name}, phase: {phase}, step: {step}, status: {status}

You are in auto-mode. DO NOT STOP. Read the state file at {state_file} for full details.

Current state summary:
- Phase: {phase} | Step: {step} | Status: {status}
- Tasks: {tasks_completed}/{tasks_total} completed
- Task states: {ts_summary}
- Active agents: {aa_summary}
- Failing gates: {failing}
- Runtime evidence: {runtime_status} | smoke: {smoke_status} | crash: {crash_detected} | hang: {hang_detected}
- Evidence dir: {evidence_dir or 'none'}
{resume_section}
Instructions by phase:
- scope/research/spec/plan: Continue from current_step={step}. Auto-decide routine choices. Log to audit trail. Proceed to next phase when done.
- execute: Check git log for commits from active agents. Advance task_states for agents that completed. Re-dispatch failed/missing tasks. Fill pool to max_parallel_agents. If all tasks done, enter gates.
- gates: Run gates in order ({failing}). Do NOT re-check passed gates. After all 7 pass, enter finalize.
- finalize: Complete local finalization, set status to DONE.

CRITICAL RULES:
1. Log every decision to .claude/auto/{task_name}/decisions.md
2. Write state.json BEFORE every state transition
3. Do NOT ask the user anything outside the 4 stop conditions
4. Do NOT stop until status is DONE
5. Check git log first if agents may have completed during your pause

Generated by auto-mode Stop hook at {ts}."""


def agent_is_tracked(state_file: str, agent_id: str) -> bool:
    """Check if an agent_id appears in the active_agents list."""
    data = load_json(state_file)
    if not data:
        return False
    return any(a.get("agent_id") == agent_id for a in data.get("active_agents", []))


def get_agent_role(state_file: str, agent_id: str) -> str:
    """Get the role of a tracked agent."""
    data = load_json(state_file)
    if not data:
        return ""
    for a in data.get("active_agents", []):
        if a.get("agent_id") == agent_id:
            return a.get("role", "")
    return ""


def has_pending_tasks(state_file: str) -> bool:
    """Check if any task_states entries have status != done/failed/passed."""
    data = load_json(state_file)
    if not data:
        return False
    return any(
        isinstance(v, dict) and v.get("status") not in ("done", "failed", "passed")
        for v in data.get("task_states", {}).values()
    )


def _is_top_level_terminal(state_file: str) -> bool:
    """Check if the state's top-level status is terminal."""
    data = load_json(state_file)
    if not data:
        return True  # no state = nothing to block on
    return data.get("status", "") in TERMINAL_STATUSES


def emit_json(obj: dict) -> None:
    """Print JSON to stdout for hook decision."""
    print(json.dumps(obj))


def emit_context_json(context: str, event_name: str) -> None:
    """Print hookSpecificOutput JSON for context injection hooks."""
    obj = {
        "hookSpecificOutput": {
            "hookEventName": event_name,
            "additionalContext": context,
        }
    }
    print(json.dumps(obj))


# ---------------------------------------------------------------------------
# SubagentStop helpers
# ---------------------------------------------------------------------------


def _check_commit_reachability(commit_sha: str) -> bool:
    """Check if a commit SHA is reachable in the current git repo."""
    if not commit_sha:
        return True
    try:
        result = subprocess.run(
            ["git", "cat-file", "-t", commit_sha],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and "commit" in result.stdout
    except Exception:
        return True  # assume reachable if git unavailable


def _check_files_touched(expected_files: list[str], commit_sha: str) -> bool:
    """Check if the commit touched any of the expected files."""
    if not expected_files or not commit_sha:
        return True
    try:
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return False
        touched = set(result.stdout.strip().splitlines())
        return any(f in touched for f in expected_files)
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Hook implementations
# ---------------------------------------------------------------------------


def hook_stop():
    """Stop hook: block if auto-mode active with nonterminal state.

    Allows stop when:
    - No active state found
    - Active state is in a terminal status (DONE, FAILED_FATAL, CANCELLED)
    - Active state has STOPPED_ASK_USER (user explicitly stopped)

    Blocks otherwise, resuming with enriched prompt.
    """
    sf = auto_mode_active()
    if not sf:
        sys.exit(0)

    # Allow stop if the state is terminal or user-initiated stop
    data = load_json(sf)
    if data:
        status = data.get("status", "")
        if status in TERMINAL_STATUSES or status == "STOPPED_ASK_USER":
            sys.exit(0)

    reason = generate_resume_prompt(sf)
    emit_json({"decision": "block", "reason": reason})
    sys.exit(0)


def hook_subagent_stop():
    """SubagentStop hook: enforce structured output and commit requirements.

    Tiers of enforcement:
    1. Structured output must exist (non-empty last_assistant_message)
    2. Gave-up language detection (for implementers)
    3. Commit SHA validation: reachability + expected files touched
       (implementers only; reviewers exempt from commit requirement)
    """
    sf = auto_mode_active()
    if not sf:
        sys.exit(0)

    raw = sys.stdin.read().strip()
    try:
        inp = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    agent_id = inp.get("agent_id", "")
    agent_type = inp.get("agent_type", "")
    last_message = inp.get("last_assistant_message", "")
    commit_sha = inp.get("commit_sha", "")
    expected_files = inp.get("expected_files", [])

    if not agent_is_tracked(sf, agent_id):
        sys.exit(0)

    role = get_agent_role(sf, agent_id)
    is_implementer = (role == "implementer" or agent_type == "general-purpose")
    is_reviewer = role == "reviewer"

    # Tier 1: empty output — structured output must exist
    if not last_message:
        if is_implementer:
            reason = ("AUTO-MODE SUBAGENT: No output. Implement the task, run tests, "
                      "commit to git. DO NOT STOP without a commit.")
        elif is_reviewer:
            reason = ("AUTO-MODE SUBAGENT: No output. Complete your review and provide "
                      "findings. DO NOT STOP without producing output.")
        else:
            reason = ("AUTO-MODE SUBAGENT: No output. Complete your task and provide "
                      "concrete results. DO NOT STOP without producing output.")
        emit_json({"decision": "block", "reason": reason})
        sys.exit(0)

    # Tier 2: gave-up language (implementers and general agents)
    if is_implementer and GAVE_UP_RE.search(last_message):
        reason = ("AUTO-MODE SUBAGENT: You appear stuck. In auto-mode, no questions "
                  "allowed. Search the codebase, pick the simplest approach, make your "
                  "own decisions. Continue working. Produce output with concrete results.")
        emit_json({"decision": "block", "reason": reason})
        sys.exit(0)

    # Tier 3: commit validation — implementers only, reviewers exempt
    if is_implementer:
        # If commit_sha is provided, validate it
        if commit_sha:
            if not _check_commit_reachability(commit_sha):
                reason = (f"AUTO-MODE SUBAGENT: Commit {commit_sha} is not reachable. "
                          f"Ensure your changes are committed to a reachable ref.")
                emit_json({"decision": "block", "reason": reason})
                sys.exit(0)

            if expected_files and not _check_files_touched(expected_files, commit_sha):
                reason = (f"AUTO-MODE SUBAGENT: Commit {commit_sha} does not touch any "
                          f"expected files: {', '.join(expected_files)}. Verify the commit "
                          f"contains the right changes.")
                emit_json({"decision": "block", "reason": reason})
                sys.exit(0)
        else:
            # No commit_sha provided — check recent git history
            try:
                result = subprocess.run(
                    ["git", "log", "--since=5 minutes ago", "--oneline"],
                    capture_output=True, text=True,
                )
                if not result.stdout.strip():
                    reason = ("AUTO-MODE SUBAGENT: No git commit. As implementer you must "
                              "produce a commit. Implemented? Tested? Committed? If yes, "
                              "mention the commit hash. If no, do the work.")
                    emit_json({"decision": "block", "reason": reason})
                    sys.exit(0)
            except Exception:
                pass

    sys.exit(0)


def hook_subagent_start():
    """SubagentStart hook: inject auto-mode context with workflow metadata.

    Attaches workflow_run_id, task_id, and expected output schema to
    the subagent context via hookSpecificOutput.
    """
    sf = auto_mode_active()
    if not sf:
        sys.exit(0)

    data = load_json(sf)

    # Read stdin for task assignment info
    task_id = ""
    expected_schema = ""
    raw = sys.stdin.read().strip()
    if raw:
        try:
            inp = json.loads(raw)
            task_id = inp.get("task_id", "")
            expected_schema = inp.get("expected_output_schema", "")
        except json.JSONDecodeError:
            pass

    task_name = data.get("task_name", "unknown") if data else "unknown"
    phase = data.get("phase", "unknown") if data else "unknown"
    workflow_run_id = data.get("workflow_run_id", "") if data else ""

    # Build structured metadata section
    meta_lines = []
    if workflow_run_id:
        meta_lines.append(f"workflow_run_id: {workflow_run_id}")
    if task_id:
        meta_lines.append(f"task_id: {task_id}")
    if expected_schema:
        meta_lines.append(f"expected_output_schema: {expected_schema}")

    meta_section = ""
    if meta_lines:
        meta_section = "\nMetadata:\n" + "\n".join(f"- {line}" for line in meta_lines)

    context = f"""<AUTO-MODE-CONTEXT>
You are a subagent in an auto-mode pipeline (task: {task_name}, phase: {phase}).
The main agent runs autonomously and expects you to complete your task without questions.

RULES:
1. Make all decisions yourself — do NOT ask clarifying questions
2. Search the codebase if you need context
3. Always commit your work to git before stopping
4. Follow existing project patterns
5. Debug and fix test failures yourself
6. Output concrete results: files changed, commits made
7. Do NOT stop with "I need more information"
8. Pick the simplest working approach if unsure
{meta_section}
State file: {sf}
</AUTO-MODE-CONTEXT>"""
    emit_context_json(context, "SubagentStart")
    sys.exit(0)


def hook_pre_compact():
    """PreCompact hook: delegate snapshot to flow-state.py, report warnings.

    Instead of writing state directly, calls flow-state.py snapshot and
    reports any warnings from the snapshot process.
    """
    sf = auto_mode_active()
    if not sf:
        sys.exit(0)

    inp_raw = sys.stdin.read().strip()
    trigger = "auto"
    try:
        inp = json.loads(inp_raw)
        trigger = inp.get("trigger", "auto")
    except json.JSONDecodeError:
        pass

    # Delegate snapshot to flow-state.py
    snap_result = _call_flow_state_snapshot(sf, reason=f"pre-compact-{trigger}")

    if snap_result is None:
        # flow-state.py unavailable — write a basic fallback snapshot
        data = load_json(sf)
        if not data:
            sys.stderr.write("Auto-mode PreCompact WARNING: state unreadable, no snapshot taken\n")
            sys.exit(0)

        task_name = data.get("task_name", "unknown")
        snapshot_dir = f".claude/auto/{task_name}"
        snapshot_file = f"{snapshot_dir}/compact-snapshot.md"
        os.makedirs(snapshot_dir, exist_ok=True)

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        phase = data.get("phase", "?")
        status = data.get("status", "?")

        fallback = f"""# Auto-Mode Compaction Snapshot (fallback)

**Created:** {ts}
**Trigger:** {trigger}
**WARNING:** flow-state.py unavailable, fallback snapshot.

Phase: {phase}
Status: {status}
State file: {sf}
"""
        with open(snapshot_file, "w", encoding="utf-8") as f:
            f.write(fallback)

        sys.stderr.write(
            "Auto-mode PreCompact WARNING: flow-state.py unavailable, "
            "fallback snapshot written\n"
        )
        sys.exit(0)

    # Check for warnings in snapshot output
    if not snap_result.get("ok"):
        errors = snap_result.get("errors", [])
        sys.stderr.write(
            f"Auto-mode PreCompact WARNING: snapshot failed: "
            f"{'; '.join(str(e) for e in errors)}\n"
        )
    else:
        snap_seq = snap_result.get("snapshot_seq", "?")
        revision = snap_result.get("revision", "?")
        sys.stderr.write(
            f"Auto-mode: PreCompact snapshot via flow-state.py "
            f"(seq={snap_seq}, rev={revision})\n"
        )

    sys.exit(0)


def hook_teammate_idle():
    """TeammateIdle hook: block teammate idle if unfinished tasks remain.

    Treats task states with status blocked/stalled/failed as unfinished
    unless the top-level state is terminal.
    """
    sf = auto_mode_active()
    if not sf:
        sys.exit(0)

    raw = sys.stdin.read().strip()
    try:
        inp = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    team_name = inp.get("team_name", "")
    if not team_name:
        sys.exit(0)

    # If top-level state is terminal, allow idle
    if _is_top_level_terminal(sf):
        sys.exit(0)

    # Check for unfinished tasks — including blocked/stalled/failed
    data = load_json(sf)
    if not data:
        sys.exit(0)

    task_states = data.get("task_states", {})
    unfinished_statuses = set()
    for tid, ts in task_states.items():
        if not isinstance(ts, dict):
            continue
        status = ts.get("status", "")
        if status not in ("done", "passed"):
            unfinished_statuses.add(f"{tid}={status}")

    if unfinished_statuses:
        teammate_name = inp.get("teammate_name", "unknown")
        summary = ", ".join(sorted(unfinished_statuses))
        sys.stderr.write(
            f"AUTO-MODE: {teammate_name} going idle but unfinished tasks remain "
            f"({summary}). Check {sf}. Pick up next task.\n"
        )
        sys.exit(2)

    sys.exit(0)


# ---------- Main dispatch ----------

COMMANDS = {
    "stop": hook_stop,
    "subagent-stop": hook_subagent_stop,
    "subagent-start": hook_subagent_start,
    "pre-compact": hook_pre_compact,
    "teammate-idle": hook_teammate_idle,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: auto-mode-hooks.py <command>", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    fn = COMMANDS.get(cmd)
    if not fn:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)
    fn()
