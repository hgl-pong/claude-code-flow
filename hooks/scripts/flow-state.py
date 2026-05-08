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
PLAN_BRIEF_FILE = os.path.join(FLOW_DIR, "plan-brief.md")
SNAPSHOT_DIR = os.path.join(FLOW_DIR, "snapshots")
ARCHIVE_DIR = os.path.join(FLOW_DIR, "archive")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")


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
        "tasks": [],
        "created_at": "",
        "updated_at": "",
        "plan_hash": None,
    }


def plan_hash(plan):
    payload = {
        key: value
        for key, value in plan.items()
        if key not in {"created_at", "updated_at", "plan_hash"}
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


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
    return base


def save_state(state):
    os.makedirs(FLOW_DIR, exist_ok=True)
    state["updated_at"] = now()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


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


def snapshot():
    state = load_state()
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap_path = os.path.join(SNAPSHOT_DIR, f"{ts}.json")
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    return snap_path


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
        state = json.load(f)
    state["session_id"] = get_session_id()
    state["updated_at"] = now()
    save_state(state)
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
            snap_state = json.load(f)
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
        result.append(
            {
                "file": snap,
                "phase": data.get("phase", "unknown"),
                "task_done": data.get("task_done", 0),
                "task_total": data.get("task_total", 0),
                "mode": data.get("mode", "standard"),
                "session_id": data.get("session_id", ""),
                "updated_at": data.get("updated_at", ""),
                "plan_hash": data.get("plan_hash"),
                "plan_status": data.get("plan_status"),
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
            state["phase_history"].append({"from": old_phase, "to": phase, "at": now()})
        state["phase"] = phase
        save_state(state)

    elif action == "set-tasks":
        done = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        total = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        state = load_state()
        state["task_done"] = done
        state["task_total"] = total
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
                print(f"  [{phase}] tasks={tasks} mode={mode} updated={ts}{plan}")

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
        plan = load_plan()
        summary = " ".join(sys.argv[2:]).strip()
        plan["approved"] = True
        plan["status"] = "approved"
        if summary:
            plan["summary"] = summary
        plan = save_plan_and_state(plan)
        export_plan(plan)
        print(json.dumps(plan, indent=2))

    elif action == "plan-export":
        path = PLAN_BRIEF_FILE if len(sys.argv) <= 2 else sys.argv[2]
        plan = load_plan()
        plan = save_plan_and_state(plan)
        output = export_plan(plan, path)
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

    elif action == "ulw-init":
        prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        state = load_state()
        state["ulw"] = {
            "active": True,
            "prompt": prompt,
            "intent": None,
            "task_done": 0,
            "task_total": 0,
        }
        state["mode"] = "autonomous"
        state["phase"] = "plan"
        save_state(state)
        print("ULW_INIT: mode=autonomous phase=plan")

    elif action == "ulw-set-intent":
        intent = sys.argv[2] if len(sys.argv) > 2 else "implement"
        state = load_state()
        if "ulw" in state:
            state["ulw"]["intent"] = intent
        save_state(state)
        print(f"ULW_INTENT: {intent}")

    elif action == "ulw-set-total":
        total = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        state = load_state()
        if "ulw" in state:
            state["ulw"]["task_total"] = total
        state["task_done"] = state.get("task_done", 0)
        state["task_total"] = total
        save_state(state)
        print(f"ULW_TOTAL: {total}")

    elif action == "ulw-inc-done":
        state = load_state()
        if "ulw" in state:
            state["ulw"]["task_done"] = state["ulw"].get("task_done", 0) + 1
        done = state.get("task_done", 0)
        state["task_done"] = done + 1
        save_state(state)
        print(done + 1)

    elif action == "uli-init":
        goal = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        max_iter = 10
        state = load_state()
        state["uli"] = {
            "active": True,
            "goal": goal,
            "iteration": 1,
            "max_iterations": max_iter,
            "current_phase": "init",
            "pd_proposal_ready": False,
            "acceptance_status": None,
            "retry_count": 0,
        }
        state["mode"] = "autonomous"
        state["phase"] = "plan"
        save_state(state)
        uli_dir = os.path.join(FLOW_DIR, "uli", "iterations")
        os.makedirs(uli_dir, exist_ok=True)
        print(f"ULI_INIT: iteration=1 max={max_iter} dir={uli_dir}")

    elif action == "uli-set-phase":
        phase = sys.argv[2] if len(sys.argv) > 2 else "plan"
        state = load_state()
        if "uli" in state:
            state["uli"]["current_phase"] = phase
        save_state(state)

    elif action == "uli-next":
        state = load_state()
        if "uli" in state:
            state["uli"]["iteration"] += 1
            state["uli"]["current_phase"] = "pd_generating"
            state["uli"]["pd_proposal_ready"] = False
            state["uli"]["acceptance_status"] = None
            state["uli"]["retry_count"] = 0
        save_state(state)
        print(state["uli"]["iteration"])

    elif action == "uli-get":
        state = load_state()
        print(json.dumps(state.get("uli", {}), indent=2))

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
