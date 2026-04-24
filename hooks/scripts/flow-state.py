#!/usr/bin/env python
"""Manage workflow state file. Usage: flow-state.py <action> [args]"""
import json, os, sys, shutil, glob
from datetime import datetime, timezone

FLOW_DIR = os.path.join(".claude", "flow")
STATE_FILE = os.path.join(FLOW_DIR, "workflow-state.json")
SNAPSHOT_DIR = os.path.join(FLOW_DIR, "snapshots")
ARCHIVE_DIR = os.path.join(FLOW_DIR, "archive")
SESSION_ID_FILE = os.path.join(FLOW_DIR, "session-id.txt")

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def get_session_id():
    if os.path.exists(SESSION_ID_FILE):
        with open(SESSION_ID_FILE, "r") as f:
            return f.read().strip()
    sid = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + os.urandom(3).hex()
    os.makedirs(FLOW_DIR, exist_ok=True)
    with open(SESSION_ID_FILE, "w") as f:
        f.write(sid)
    return sid

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
        "retry_count": 0,
    }

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return default_state()
    return default_state()

def save_state(state):
    os.makedirs(FLOW_DIR, exist_ok=True)
    state["updated_at"] = now()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def snapshot():
    """Save current state to snapshot directory."""
    state = load_state()
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    snap_path = os.path.join(SNAPSHOT_DIR, f"{ts}.json")
    with open(snap_path, "w") as f:
        json.dump(state, f, indent=2)
    return snap_path

def resume():
    """Resume from the latest snapshot."""
    if not os.path.exists(SNAPSHOT_DIR):
        print("No snapshots available", file=sys.stderr)
        sys.exit(1)
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))
    if not snapshots:
        print("No snapshots available", file=sys.stderr)
        sys.exit(1)
    latest = snapshots[-1]
    with open(latest, "r") as f:
        state = json.load(f)
    state["session_id"] = get_session_id()
    state["updated_at"] = now()
    save_state(state)
    return latest

def archive():
    """Move completed snapshots to archive."""
    if not os.path.exists(SNAPSHOT_DIR):
        return 0
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))
    state = load_state()
    moved = 0
    for snap in snapshots:
        basename = os.path.basename(snap)
        # Keep snapshots from the current session
        with open(snap, "r") as f:
            snap_state = json.load(f)
        if snap_state.get("session_id") != state.get("session_id"):
            dest = os.path.join(ARCHIVE_DIR, basename)
            shutil.move(snap, dest)
            moved += 1
    return moved

def list_snapshots():
    """List all available snapshots."""
    if not os.path.exists(SNAPSHOT_DIR):
        return []
    snapshots = sorted(glob.glob(os.path.join(SNAPSHOT_DIR, "*.json")))
    result = []
    for snap in snapshots:
        with open(snap, "r") as f:
            data = json.load(f)
        result.append({
            "file": snap,
            "phase": data.get("phase", "unknown"),
            "task_done": data.get("task_done", 0),
            "task_total": data.get("task_total", 0),
            "mode": data.get("mode", "standard"),
            "session_id": data.get("session_id", ""),
            "updated_at": data.get("updated_at", ""),
        })
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
        with open(error_log, "a") as f:
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
                tasks = f'{s["task_done"]}/{s["task_total"]}'
                mode = s["mode"]
                ts = s["updated_at"]
                print(f"  [{phase}] tasks={tasks} mode={mode} updated={ts}")

    elif action == "clear":
        snapshot()
        os.makedirs(FLOW_DIR, exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump(default_state(), f)
        for fname in ["modified-files.txt", "review-result.txt"]:
            fpath = os.path.join(FLOW_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)

    elif action == "get":
        state = load_state()
        print(json.dumps(state, indent=2))

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
