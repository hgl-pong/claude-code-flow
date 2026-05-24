#!/usr/bin/env python
"""Manage workflow state file. Usage: flow-state.py <action> [args]"""
import glob
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")
PLAN_FILE = os.path.join(FLOW_DIR, "plan-state.json")
ULI_STATE_FILE = os.path.join(FLOW_DIR, "uli-state.json")
PLAN_BRIEF_FILE = os.path.join(FLOW_DIR, "plan-brief.md")  # legacy default; pass --output for slug-namespaced paths
SNAPSHOT_DIR = os.path.join(FLOW_DIR, "snapshots")
ARCHIVE_DIR = os.path.join(FLOW_DIR, "archive")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")
EXEC_LOG_FILE = os.path.join(FLOW_DIR, "exec-log.jsonl")
EVIDENCE_FILE = os.path.join(FLOW_DIR, "verification-evidence.jsonl")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_session_id():
    if os.path.exists(SESSION_ID_FILE):
        with open(SESSION_ID_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    sid = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(3).hex()
    os.makedirs(FLOW_DIR, exist_ok=True)
    with open(SESSION_ID_FILE, "w", encoding="utf-8") as f:
        f.write(sid)
    return sid


def default_plan():
    return {
        "title": "",
        "goal": "",
        "mode": "standard",
        "status": "draft",
        "source": "",
        "approved": False,
        "summary": "",
        "output_dir": "",
        "tasks": [],
        "created_at": "",
        "updated_at": "",
        "plan_hash": None,
    }


def slugify(text):
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in text).strip("-")
    parts = [part for part in slug.split("-") if part]
    return "-".join(parts)[:80] or "plan"

def default_output_dir(plan):
    title = plan.get("title") or plan.get("goal") or plan.get("source") or "plan"
    return os.path.join(FLOW_DIR, "plans", slugify(title))

def ensure_plan_output_dir(plan):
    output_dir = plan.get("output_dir") or default_output_dir(plan)
    plan["output_dir"] = output_dir
    os.makedirs(output_dir, exist_ok=True)
    phase_context = os.path.join(output_dir, "phase-context.md")
    if not os.path.exists(phase_context):
        title = plan.get("title") or "Plan"
        with open(phase_context, "w", encoding="utf-8") as f:
            f.write(f"# {title} Phase Context\n\n")
    return output_dir

def plan_brief_path(plan):
    return os.path.join(ensure_plan_output_dir(plan), "plan-brief.md")

def plan_hash(plan):
    payload = {
        key: value
        for key, value in plan.items()
        if key not in {"created_at", "updated_at", "plan_hash"}
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def default_resume_cursor():
    return {
        "current_gate": None,
        "active_batch": [],
        "ready_task_ids": [],
        "blocked_task_ids": [],
        "agent_dispatches": [],
        "worktrees": [],
        "last_checkpoint": None,
        "next_action": None,
    }


def default_state():
    return {
        "session_id": get_session_id(),
        "phase": "idle",
        "task_done": 0,
        "task_total": 0,
        "updated_at": "",
        "created_at": now(),
        "mode": "standard",
        "current_agent": None,
        "phase_history": [],
        "plan_hash": None,
        "plan_status": None,
        "plan_title": None,
        "plan_goal": None,
        "plan_task_total": 0,
        "retry_count": 0,
        "verification_count": 0,
        "last_verification": None,
        "resume_cursor": default_resume_cursor(),
    }


def load_state():
    base = default_state()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                state = json.load(f)
                if isinstance(state, dict):
                    base.update(state)
            except json.JSONDecodeError:
                pass
    cursor = default_resume_cursor()
    if isinstance(base.get("resume_cursor"), dict):
        cursor.update(base["resume_cursor"])
    base["resume_cursor"] = cursor
    return base


def append_event(event_type, **payload):
    os.makedirs(FLOW_DIR, exist_ok=True)
    entry = {
        "ts": now(),
        "session_id": get_session_id(),
        "type": event_type,
    }
    entry.update({k: v for k, v in payload.items() if v is not None})
    with open(EXEC_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    return entry


def update_resume_cursor(state, **updates):
    cursor = default_resume_cursor()
    if isinstance(state.get("resume_cursor"), dict):
        cursor.update(state["resume_cursor"])
    cursor.update({k: v for k, v in updates.items() if k in cursor})
    state["resume_cursor"] = cursor
    return state


def save_state(state):
    os.makedirs(FLOW_DIR, exist_ok=True)
    state["updated_at"] = now()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def sync_uli_state_file(uli: dict) -> None:
    """Keep uli-state.json in sync so the stop hook (bash) can read it directly."""
    os.makedirs(FLOW_DIR, exist_ok=True)
    flat = {
        "active": uli.get("active", True),
        "session_id": uli.get("session_id", get_session_id()),
        "goal": uli.get("goal", ""),
        "iteration": uli.get("iteration", 1),
        "max_iterations": uli.get("max_iterations", 10),
        "current_phase": uli.get("current_phase", "init"),
        "current_task_slug": uli.get("current_task_slug", ""),
        "pd_proposal_ready": uli.get("pd_proposal_ready", False),
        "acceptance_status": uli.get("acceptance_status"),
        "started_at": uli.get("started_at", now()),
        "last_iteration_at": uli.get("last_iteration_at", now()),
    }
    with open(ULI_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(flat, f, indent=2)


def load_plan():
    base = default_plan()
    if os.path.exists(PLAN_FILE):
        with open(PLAN_FILE, "r", encoding="utf-8") as f:
            try:
                plan = json.load(f)
                if isinstance(plan, dict):
                    base.update(plan)
            except json.JSONDecodeError:
                pass
    return base


def save_plan(plan):
    os.makedirs(FLOW_DIR, exist_ok=True)
    ensure_plan_output_dir(plan)
    if not plan.get("created_at"):
        plan["created_at"] = now()
    plan["updated_at"] = now()
    plan["plan_hash"] = plan_hash(plan)
    with open(PLAN_FILE, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2)
    return plan


def sync_plan_state(state, plan):
    tasks = plan.get("tasks", [])
    if not isinstance(tasks, list):
        tasks = []
    state["plan_hash"] = plan.get("plan_hash")
    state["plan_status"] = plan.get("status", "draft")
    state["plan_title"] = plan.get("title", "")
    state["plan_goal"] = plan.get("goal", "")
    state["plan_task_total"] = len(tasks)
    return state


def clear_plan_state(state):
    state["plan_hash"] = None
    state["plan_status"] = None
    state["plan_title"] = None
    state["plan_goal"] = None
    state["plan_task_total"] = 0
    return state


def save_plan_and_state(plan):
    plan = save_plan(plan)
    state = load_state()
    sync_plan_state(state, plan)
    save_state(state)
    return plan


def parse_json_arg(args, start=2):
    raw = " ".join(args[start:]).strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def normalize_task(task, index):
    if isinstance(task, str):
        return {
            "id": index + 1,
            "title": task,
            "files": [],
            "test_command": "",
            "acceptance": [],
            "depends_on": [],
        }
    if not isinstance(task, dict):
        return None
    task_id = task.get("id", index + 1)
    if isinstance(task_id, str) and task_id.isdigit():
        task_id = int(task_id)
    return {
        "id": task_id,
        "title": task.get("title", task.get("goal", f"Task {index + 1}")),
        "files": task.get("files", []),
        "test_command": task.get("test_command", ""),
        "acceptance": task.get("acceptance", []),
        "depends_on": task.get("depends_on", []),
    }


def normalize_tasks(tasks):
    normalized = []
    if not isinstance(tasks, list):
        return normalized
    for index, task in enumerate(tasks):
        normalized_task = normalize_task(task, index)
        if normalized_task:
            normalized.append(normalized_task)
    return normalized


def render_plan(plan):
    lines = []
    title = plan.get("title") or "Plan"
    lines.append(f"# {title} Implementation Plan")
    lines.append("")
    lines.append(f"**Goal:** {plan.get('goal', '')}")
    lines.append(f"**Mode:** {plan.get('mode', 'standard')}")
    lines.append(f"**Status:** {plan.get('status', 'draft')}")
    lines.append(f"**Approved:** {'yes' if plan.get('approved') else 'no'}")
    if plan.get("summary"):
        lines.append(f"**Summary:** {plan.get('summary', '')}")
    if plan.get("plan_hash"):
        lines.append(f"**Plan Hash:** `{plan.get('plan_hash')}`")
    lines.append("")
    lines.append("## Tasks")
    tasks = plan.get("tasks", [])
    if not tasks:
        lines.append("- None")
    else:
        for task in tasks:
            lines.append(f"### Task {task.get('id', '?')}: {task.get('title', '')}")
            files = task.get("files", [])
            if files:
                lines.append("**Files:**")
                for file_path in files:
                    lines.append(f"- `{file_path}`")
            test_command = task.get("test_command", "")
            if test_command:
                lines.append(f"**Test:** `{test_command}`")
            acceptance = task.get("acceptance", [])
            if acceptance:
                lines.append("**Acceptance:**")
                for item in acceptance:
                    lines.append(f"- {item}")
            depends_on = task.get("depends_on", [])
            if depends_on:
                lines.append(f"**Depends on:** {', '.join(str(item) for item in depends_on)}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export_plan(plan, path=PLAN_BRIEF_FILE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = render_plan(plan)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def read_tail(path, max_lines=40):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.rstrip("\n") for line in lines[-max_lines:]]


def read_text_if_exists(path, max_chars=20000):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = f.read(max_chars + 1)
    return data[:max_chars]


def snapshot():
    state = load_state()
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap_path = os.path.join(SNAPSHOT_DIR, f"{ts}.json")
    bundle = {
        "format": "workflow-snapshot-v2",
        "created_at": now(),
        "workflow_state": state,
        "plan_state": load_plan(),
        "exec_log_tail": read_tail(EXEC_LOG_FILE),
        "verification_evidence_tail": read_tail(EVIDENCE_FILE),
        "phase_context": read_text_if_exists(os.path.join(FLOW_DIR, "phase-context.md")),
        "plan_brief": read_text_if_exists(PLAN_BRIEF_FILE),
    }
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)
    state = update_resume_cursor(state, last_checkpoint=snap_path)
    save_state(state)
    append_event("checkpoint", checkpoint=snap_path, phase=state.get("phase"))
    return snap_path


def state_from_snapshot(data):
    if isinstance(data, dict) and data.get("format") == "workflow-snapshot-v2":
        state = data.get("workflow_state", {})
        return state if isinstance(state, dict) else {}
    return data if isinstance(data, dict) else {}


def resume():
    if not os.path.exists(SNAPSHOT_DIR):
        print("No snapshots available", file=sys.stderr)
        sys.exit(1)
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))
    if not snapshots:
        print("No snapshots available", file=sys.stderr)
        sys.exit(1)
    latest = snapshots[-1]
    with open(latest, "r", encoding="utf-8") as f:
        state = state_from_snapshot(json.load(f))
    state["session_id"] = get_session_id()
    state["updated_at"] = now()
    state = update_resume_cursor(state, last_checkpoint=latest)
    save_state(state)
    append_event("resume", checkpoint=latest, phase=state.get("phase"), next_action=state.get("resume_cursor", {}).get("next_action"))
    return latest


def archive():
    if not os.path.exists(SNAPSHOT_DIR):
        return 0
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))
    state = load_state()
    moved = 0
    for snap in snapshots:
        basename = os.path.basename(snap)
        with open(snap, "r", encoding="utf-8") as f:
            snap_state = state_from_snapshot(json.load(f))
        if snap_state.get("session_id") != state.get("session_id"):
            shutil.move(snap, os.path.join(ARCHIVE_DIR, basename))
            moved += 1
    return moved


def list_snapshots():
    if not os.path.exists(SNAPSHOT_DIR):
        return []
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))
    result = []
    for snap in snapshots:
        with open(snap, "r", encoding="utf-8") as f:
            data = json.load(f)
        state = state_from_snapshot(data)
        result.append(
            {
                "file": snap,
                "phase": state.get("phase", "unknown"),
                "task_done": state.get("task_done", 0),
                "task_total": state.get("task_total", 0),
                "mode": state.get("mode", "standard"),
                "session_id": state.get("session_id", ""),
                "updated_at": state.get("updated_at", data.get("created_at", "")),
                "plan_hash": state.get("plan_hash"),
                "plan_status": state.get("plan_status"),
                "next_action": state.get("resume_cursor", {}).get("next_action"),
            }
        )
    return result


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else ""

    if action == "set-phase":
        phase = sys.argv[2] if len(sys.argv) > 2 else "idle"
        state = load_state()
        old_phase = state["phase"]
        if old_phase != phase:
            event = {"from": old_phase, "to": phase, "at": now()}
            state["phase_history"].append(event)
            append_event("phase_transition", **event)
        state["phase"] = phase
        state = update_resume_cursor(state, current_gate=phase, next_action=f"continue {phase} phase")
        save_state(state)

    elif action == "set-tasks":
        done = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        total = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        state = load_state()
        state["task_done"] = done
        state["task_total"] = total
        append_event("task_progress", done=done, total=total, phase=state.get("phase"))
        save_state(state)

    elif action == "set-agent":
        agent = sys.argv[2] if len(sys.argv) > 2 else ""
        state = load_state()
        state["current_agent"] = agent if agent else None
        save_state(state)

    elif action == "set-mode":
        mode = sys.argv[2] if len(sys.argv) > 2 else "standard"
        state = load_state()
        state["mode"] = mode
        save_state(state)

    elif action == "push-history":
        from_phase = sys.argv[2] if len(sys.argv) > 2 else "unknown"
        to_phase = sys.argv[3] if len(sys.argv) > 3 else "unknown"
        state = load_state()
        state["phase_history"].append({"from": from_phase, "to": to_phase, "at": now()})
        save_state(state)

    elif action == "inc-retry":
        state = load_state()
        state["retry_count"] = state.get("retry_count", 0) + 1
        save_state(state)
        print(state["retry_count"])

    elif action == "set-error":
        task_id = sys.argv[2] if len(sys.argv) > 2 else ""
        error_type = sys.argv[3] if len(sys.argv) > 3 else "unknown"
        message = " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""
        error_log = os.path.join(FLOW_DIR, "error-log.jsonl")
        os.makedirs(FLOW_DIR, exist_ok=True)
        entry = {
            "ts": now(),
            "session_id": get_session_id(),
            "task_id": task_id,
            "error_type": error_type,
            "message": message,
        }
        with open(error_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    elif action == "snapshot":
        path = snapshot()
        print(f"SNAPSHOT: {path}")

    elif action == "resume":
        path = resume()
        print(f"RESUMED: {path}")

    elif action == "archive":
        count = archive()
        print(f"ARCHIVED: {count} snapshots")

    elif action == "list-snapshots":
        snaps = list_snapshots()
        if not snaps:
            print("No snapshots available")
        else:
            for s in snaps:
                phase = s["phase"]
                tasks = f"{s['task_done']}/{s['task_total']}"
                mode = s["mode"]
                ts = s["updated_at"]
                plan = f" plan={s['plan_status'] or 'none'}:{s['plan_hash'] or 'none'}"
                next_action = f" next={s['next_action']}" if s.get("next_action") else ""
                print(f"  [{phase}] tasks={tasks} mode={mode} updated={ts}{plan}{next_action}")

    elif action == "clear":
        snapshot()
        os.makedirs(FLOW_DIR, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(default_state(), f, indent=2)
        for path in [PLAN_FILE, PLAN_BRIEF_FILE]:
            if os.path.exists(path):
                os.remove(path)
        for fname in ["modified-files.jsonl", "review-result.txt", "verification-evidence.jsonl", "last-verification.json"]:
            fpath = os.path.join(FLOW_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)

    elif action == "get":
        state = load_state()
        print(json.dumps(state, indent=2))

    elif action == "plan-init":
        plan = load_plan()
        payload = parse_json_arg(sys.argv)
        if payload:
            plan.update({k: v for k, v in payload.items() if k not in {"tasks", "plan_hash", "created_at", "updated_at"}})
            if isinstance(payload.get("tasks"), list):
                plan["tasks"] = normalize_tasks(payload["tasks"])
        else:
            text = " ".join(sys.argv[2:]).strip()
            if text:
                plan["title"] = text
                plan["goal"] = text
                plan["source"] = text
        plan.setdefault("status", "draft")
        plan.setdefault("approved", False)
        plan = save_plan_and_state(plan)
        print(json.dumps(plan, indent=2))

    elif action == "plan-update":
        plan = load_plan()
        payload = parse_json_arg(sys.argv)
        if payload:
            for key, value in payload.items():
                if key in {"created_at", "updated_at", "plan_hash"}:
                    continue
                plan[key] = value
        else:
            text = " ".join(sys.argv[2:]).strip()
            if text:
                plan["summary"] = text
        plan = save_plan_and_state(plan)
        print(json.dumps(plan, indent=2))

    elif action == "plan-add-task":
        plan = load_plan()
        payload = parse_json_arg(sys.argv)
        task = None
        if payload:
            task = normalize_task(payload, len(plan.get("tasks", [])))
        else:
            text = " ".join(sys.argv[2:]).strip()
            if text:
                task = normalize_task(text, len(plan.get("tasks", [])))
        if task:
            tasks = plan.get("tasks", [])
            if not isinstance(tasks, list):
                tasks = []
            tasks.append(task)
            plan["tasks"] = tasks
        plan = save_plan_and_state(plan)
        print(json.dumps(plan, indent=2))

    elif action == "plan-approve":
        args = sys.argv[2:]
        path = None
        if "--output" in args:
            idx = args.index("--output")
            if idx + 1 >= len(args):
                print("ERROR: --output requires a path argument", file=sys.stderr)
                sys.exit(1)
            path = args[idx + 1]
            args = args[:idx] + args[idx + 2:]
        summary = " ".join(args).strip()
        plan = load_plan()
        plan["approved"] = True
        plan["status"] = "approved"
        if summary:
            plan["summary"] = summary
        plan = save_plan_and_state(plan)
        output = export_plan(plan, path or plan_brief_path(plan))
        if output != PLAN_BRIEF_FILE:
            export_plan(plan, PLAN_BRIEF_FILE)
        print(json.dumps(plan, indent=2))

    elif action == "plan-export":
        explicit_path = len(sys.argv) > 2
        plan = load_plan()
        plan = save_plan_and_state(plan)
        path = sys.argv[2] if explicit_path else plan_brief_path(plan)
        output = export_plan(plan, path)
        if not explicit_path and output != PLAN_BRIEF_FILE:
            export_plan(plan, PLAN_BRIEF_FILE)
        print(f"PLAN_EXPORTED: {output}")

    elif action == "plan-get":
        print(json.dumps(load_plan(), indent=2))

    elif action == "plan-clear":
        state = load_state()
        clear_plan_state(state)
        save_state(state)
        if os.path.exists(PLAN_FILE):
            os.remove(PLAN_FILE)
        if os.path.exists(PLAN_BRIEF_FILE):
            os.remove(PLAN_BRIEF_FILE)
        print("PLAN_CLEARED")

    elif action == "uli-init":
        goal = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        max_iter = 10
        state = load_state()
        state["uli"] = {
            "active": True,
            "session_id": get_session_id(),
            "goal": goal,
            "iteration": 1,
            "max_iterations": max_iter,
            "current_phase": "init",
            "current_task_slug": "",
            "pd_proposal_ready": False,
            "acceptance_status": None,
            "retry_count": 0,
            "started_at": now(),
            "last_iteration_at": now(),
        }
        state["mode"] = "autonomous"
        state["phase"] = "plan"
        save_state(state)
        sync_uli_state_file(state["uli"])
        uli_dir = os.path.join(FLOW_DIR, "uli")
        os.makedirs(uli_dir, exist_ok=True)
        print(f"ULI_INIT: iteration=1 max={max_iter} dir={uli_dir}")

    elif action == "uli-set-task":
        slug = sys.argv[2] if len(sys.argv) > 2 else "task"
        state = load_state()
        if "uli" not in state:
            print("WARNING: uli-set-task called before uli-init — slug stored but other fields may be missing", file=sys.stderr)
            state["uli"] = {}
        state["uli"]["current_task_slug"] = slug
        save_state(state)
        sync_uli_state_file(state["uli"])
        task_dir = os.path.join(FLOW_DIR, "uli", slug)
        os.makedirs(task_dir, exist_ok=True)
        print(f"ULI_SET_TASK: slug={slug} dir={task_dir}")

    elif action == "uli-set-total":
        total = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        state = load_state()
        state["task_done"] = state.get("task_done", 0)
        state["task_total"] = total
        if "uli" in state:
            state["uli"]["task_total"] = total
            sync_uli_state_file(state["uli"])
        save_state(state)
        print(f"ULI_TOTAL: {total}")

    elif action == "uli-inc-done":
        state = load_state()
        done = state.get("task_done", 0) + 1
        state["task_done"] = done
        if "uli" in state:
            state["uli"]["task_done"] = state["uli"].get("task_done", 0) + 1
            sync_uli_state_file(state["uli"])
        save_state(state)
        print(done)

    elif action == "uli-set-phase":
        phase = sys.argv[2] if len(sys.argv) > 2 else "plan"
        state = load_state()
        if "uli" not in state:
            print("WARNING: uli-set-phase called before uli-init", file=sys.stderr)
        else:
            state["uli"]["current_phase"] = phase
        save_state(state)
        if "uli" in state:
            sync_uli_state_file(state["uli"])

    elif action == "uli-next":
        state = load_state()
        if "uli" in state:
            state["uli"]["iteration"] += 1
            state["uli"]["current_phase"] = "pd_generating"
            state["uli"]["current_task_slug"] = ""
            state["uli"]["pd_proposal_ready"] = False
            state["uli"]["acceptance_status"] = None
            state["uli"]["retry_count"] = 0
            state["uli"]["last_iteration_at"] = now()
        save_state(state)
        if "uli" in state:
            sync_uli_state_file(state["uli"])
        print(state["uli"]["iteration"])

    elif action == "uli-get":
        state = load_state()
        print(json.dumps(state.get("uli", {}), indent=2))

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
