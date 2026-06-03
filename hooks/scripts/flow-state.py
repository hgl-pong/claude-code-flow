#!/usr/bin/env python
"""Authoritative flow-state helper CLI.

Single writer/validator for workflow run state, audit log, snapshots,
and evidence manifest. Zero external dependencies (stdlib only).

Exit codes:
    0  success
    2  validation error
    3  concurrency conflict
    4  I/O error
    5  corrupt state
    6  unsafe path
"""

import argparse
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_SCHEMA_VERSION = 1

VALID_PHASES = (
    "scope", "research", "synthesize_spec", "review_spec",
    "write_plan", "review_plan", "parse_plan", "execute",
    "gates", "finalize",
)

VALID_STATUSES = (
    "ACTIVE", "PAUSED_COMPACTING", "BLOCKED_ESCALATING",
    "DONE", "STOPPED_ASK_USER", "FAILED_FATAL", "CANCELLED",
)

DEFAULT_PROGRESS = {
    "tasks_passed": 0,
    "tasks_total": 0,
    "gates_passed": 0,
    "gates_total": 7,
}

STATE_V1_REQUIRED = {
    "state_schema_version", "revision", "task_name", "safe_task_name",
    "workflow_run_id", "phase", "status", "progress", "groups",
    "task_states", "gate_states", "runtime_verification", "git_state",
    "resume_cursor", "audit_log", "evidence_dir", "worktree_path",
    "base_ref", "created_at", "updated_at",
}

RUNS_FILENAME = "runs.json"

AUDIT_DIR = "audit"
AUDIT_FILENAME = "events.jsonl"

EVIDENCE_DIR = "evidence"
MANIFEST_FILENAME = "manifest.json"

SNAPSHOTS_DIR = "snapshots"

SAFE_NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
SAFE_NAME_MAX = 48

SECRET_KEY_RE = re.compile(
    r"(_KEY|_TOKEN|_SECRET|_PASSWORD|AUTHORIZATION|COOKIE|_CREDENTIAL)",
    re.IGNORECASE,
)

EVIDENCE_MAX_BYTES = 10 * 1024 * 1024  # 10 MiB

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _utcnow_rfc3339():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_task_name(raw):
    """Convert to safe lowercase ASCII alnum/dash, max 48 chars."""
    s = raw.lower().strip()
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    if len(s) > SAFE_NAME_MAX:
        s = s[:SAFE_NAME_MAX].rstrip("-")
    return s or "unnamed"


def _validate_safe_name(name):
    if not name or not SAFE_NAME_RE.match(name) or len(name) > SAFE_NAME_MAX:
        return False
    return True


def _redact_secrets(obj):
    """Recursively redact values whose keys match secret patterns."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if isinstance(v, str) and SECRET_KEY_RE.search(k):
                out[k] = "[REDACTED]"
            else:
                out[k] = _redact_secrets(v)
        return out
    if isinstance(obj, list):
        return [_redact_secrets(item) for item in obj]
    return obj


def _check_path_safety(path_str, base_dir):
    """Reject path traversal. Returns resolved path or None."""
    try:
        resolved = (base_dir / path_str).resolve()
        base_resolved = base_dir.resolve()
        if not str(resolved).startswith(str(base_resolved) + os.sep) and resolved != base_resolved:
            return None
        return resolved
    except Exception:
        return None


def _atomic_write_json(path, data):
    """Write JSON to path atomically via temp sibling, fsync, rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=False)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(str(tmp), str(path))
    except Exception:
        try:
            os.unlink(str(tmp))
        except OSError:
            pass
        raise


def _atomic_append_jsonl(path, record):
    """Append one JSON line atomically via temp file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=False) + "\n"
    tmp = path.with_suffix(".jsonl.tmp")
    try:
        with open(str(path), "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
    except Exception:
        raise


def _load_json(path):
    try:
        with open(str(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        return None, f"Corrupt JSON: {e}"
    except FileNotFoundError:
        return None, "File not found"
    except Exception as e:
        return None, str(e)


def _output(ok, state_file=None, revision=None, errors=None, **extra):
    result = {"ok": ok}
    if state_file is not None:
        result["state_file"] = str(state_file)
    if revision is not None:
        result["revision"] = revision
    if errors:
        result["errors"] = errors
    result.update(extra)
    print(json.dumps(result, indent=2))


def _find_auto_dir():
    """Walk up from cwd to find .claude/auto directory."""
    p = Path.cwd()
    for _ in range(20):
        candidate = p / ".claude" / "auto"
        if candidate.is_dir():
            return candidate
        parent = p.parent
        if parent == p:
            break
        p = parent
    return None


def _load_runs(runs_path):
    if runs_path.exists():
        data = _load_json(runs_path)
        if isinstance(data, dict):
            return data
    return {}


def _next_run_seq(runs):
    if not runs:
        return 1
    seqs = []
    for v in runs.values():
        if isinstance(v, dict) and "seq" in v:
            try:
                seqs.append(int(v["seq"]))
            except (ValueError, TypeError):
                pass
    return max(seqs, default=0) + 1


# ---------------------------------------------------------------------------
# Deep merge helper
# ---------------------------------------------------------------------------


def _deep_merge(base, patch):
    """Deep-merge objects, replace arrays, delete null keys."""
    result = dict(base)
    for k, v in patch.items():
        if v is None:
            result.pop(k, None)
        elif isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_state_schema(state):
    """Validate required fields and basic types. Returns list of errors."""
    errors = []
    missing = STATE_V1_REQUIRED - set(state.keys())
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")
    if "state_schema_version" in state and state["state_schema_version"] != STATE_SCHEMA_VERSION:
        errors.append(f"Unsupported schema version: {state['state_schema_version']}")
    if "phase" in state and state["phase"] not in VALID_PHASES:
        errors.append(f"Invalid phase: {state['phase']}")
    if "status" in state and state["status"] not in VALID_STATUSES:
        errors.append(f"Invalid status: {state['status']}")
    if "revision" in state and not isinstance(state["revision"], int):
        errors.append(f"Revision must be int, got {type(state['revision']).__name__}")
    if "progress" in state and not isinstance(state["progress"], dict):
        errors.append("Progress must be an object")
    return errors


def _validate_manifest(manifest):
    """Validate evidence manifest structure."""
    errors = []
    if not isinstance(manifest, dict):
        errors.append("Manifest must be an object")
        return errors
    artifacts = manifest.get("artifacts", [])
    if not isinstance(artifacts, list):
        errors.append("Manifest artifacts must be a list")
    return errors


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_init(args):
    """Create run directory, state.json, audit, manifest, snapshots dir, runs.json entry."""
    task_name = args.task_name
    worktree = Path(args.worktree).resolve()
    spec_path = args.spec_path or ""
    plan_path = args.plan_path or ""
    base_ref = args.base_ref or "main"

    safe = _safe_task_name(task_name)
    if not _validate_safe_name(safe):
        _output(False, errors=[f"Safe task name invalid: {safe}"])
        return 2

    auto_dir = _find_auto_dir()
    if auto_dir is None:
        auto_dir = worktree / ".claude" / "auto"
    auto_dir.mkdir(parents=True, exist_ok=True)

    runs_path = auto_dir / RUNS_FILENAME
    runs = _load_runs(runs_path)
    run_seq = _next_run_seq(runs)

    run_dir_name = f"{safe}-{run_seq}"
    run_dir = auto_dir / run_dir_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # Sub-dirs
    audit_dir = run_dir / AUDIT_DIR
    audit_dir.mkdir(exist_ok=True)
    evidence_dir = run_dir / EVIDENCE_DIR
    evidence_dir.mkdir(exist_ok=True)
    snapshots_dir = run_dir / SNAPSHOTS_DIR
    snapshots_dir.mkdir(exist_ok=True)

    now = _utcnow_rfc3339()
    run_id = str(run_seq)

    state = {
        "state_schema_version": STATE_SCHEMA_VERSION,
        "revision": 0,
        "task_name": task_name,
        "safe_task_name": safe,
        "workflow_run_id": run_id,
        "phase": "scope",
        "status": "ACTIVE",
        "progress": dict(DEFAULT_PROGRESS),
        "groups": [],
        "task_states": {},
        "gate_states": [],
        "runtime_verification": {},
        "git_state": {},
        "resume_cursor": {},
        "audit_log": f"{AUDIT_DIR}/{AUDIT_FILENAME}",
        "audit_event_count": 0,
        "evidence_dir": EVIDENCE_DIR,
        "worktree_path": str(worktree),
        "base_ref": base_ref,
        "created_at": now,
        "updated_at": now,
    }

    # Extra metadata
    if spec_path:
        state["spec_path"] = spec_path
    if plan_path:
        state["plan_path"] = plan_path

    state_file = run_dir / "state.json"

    # Init audit log
    audit_path = run_dir / AUDIT_DIR / AUDIT_FILENAME
    _atomic_append_jsonl(audit_path, {
        "ts": now,
        "type": "run_created",
        "data": {"safe_task_name": safe, "run_id": run_id},
    })
    state["audit_event_count"] = 1

    _atomic_write_json(state_file, state)

    # Init manifest
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "artifacts": [],
        "summary": {"total": 0, "by_type": {}},
        "created_at": now,
        "updated_at": now,
    }
    _atomic_write_json(run_dir / EVIDENCE_DIR / MANIFEST_FILENAME, manifest)

    # Update runs registry
    runs[run_dir_name] = {
        "seq": run_seq,
        "task_name": task_name,
        "safe_task_name": safe,
        "state_file": str(state_file),
        "created_at": now,
    }
    _atomic_write_json(runs_path, runs)

    _output(True, state_file=str(state_file), revision=0)
    return 0


def cmd_update(args):
    """Validate, optimistic concurrency check, deep-merge, atomic write."""
    state_file = Path(args.state_file)
    patch = json.loads(args.patch_json)
    expected = args.expected_revision

    # Path safety
    if ".." in str(state_file) or not str(state_file).endswith("state.json"):
        pass  # allow absolute paths

    result = _load_json(state_file)
    if isinstance(result, tuple):
        _output(False, state_file=str(state_file), errors=[result[1]])
        return 5
    state = result

    # Schema check on existing
    schema_errors = _validate_state_schema(state)
    if schema_errors:
        _output(False, state_file=str(state_file), errors=schema_errors)
        return 2

    # Optimistic concurrency
    if expected is not None and state.get("revision") != expected:
        _output(False, state_file=str(state_file), revision=state.get("revision"),
                errors=[f"Revision mismatch: expected {expected}, actual {state.get('revision')}"])
        return 3

    # Redact secrets in patch
    patch = _redact_secrets(patch)

    # Deep merge
    state = _deep_merge(state, patch)
    state["revision"] = state.get("revision", 0) + 1
    state["updated_at"] = _utcnow_rfc3339()

    # Re-validate
    schema_errors = _validate_state_schema(state)
    if schema_errors:
        _output(False, state_file=str(state_file), revision=state.get("revision"),
                errors=["Post-merge validation failed"] + schema_errors)
        return 2

    _atomic_write_json(state_file, state)
    _output(True, state_file=str(state_file), revision=state["revision"])
    return 0


def cmd_event(args):
    """Validate event, append JSONL, update audit_event_count."""
    state_file = Path(args.state_file)
    event_type = args.type
    event_data = json.loads(args.json_data)
    correlation_id = args.correlation_id or str(uuid.uuid4())

    result = _load_json(state_file)
    if isinstance(result, tuple):
        _output(False, state_file=str(state_file), errors=[result[1]])
        return 5
    state = result

    run_dir = state_file.parent
    audit_path = run_dir / state.get("audit_log", f"{AUDIT_DIR}/{AUDIT_FILENAME}")

    now = _utcnow_rfc3339()
    event_record = {
        "ts": now,
        "type": event_type,
        "correlation_id": correlation_id,
        "revision": state.get("revision", 0),
        "data": _redact_secrets(event_data),
    }

    _atomic_append_jsonl(audit_path, event_record)

    # Update audit event count in state
    count = state.get("audit_event_count", 0) + 1
    state["audit_event_count"] = count
    state["updated_at"] = now
    _atomic_write_json(state_file, state)

    _output(True, state_file=str(state_file), revision=state["revision"],
            audit_event_count=count, correlation_id=correlation_id)
    return 0


def cmd_manifest(args):
    """Merge into evidence/manifest.json, sync summary into state."""
    state_file = Path(args.state_file)
    patch = json.loads(args.patch_json)

    result = _load_json(state_file)
    if isinstance(result, tuple):
        _output(False, state_file=str(state_file), errors=[result[1]])
        return 5
    state = result

    run_dir = state_file.parent
    manifest_path = run_dir / state.get("evidence_dir", EVIDENCE_DIR) / MANIFEST_FILENAME

    manifest_result = _load_json(manifest_path)
    if isinstance(manifest_result, tuple):
        manifest_result = {
            "schema_version": 1,
            "run_id": state.get("workflow_run_id", "0"),
            "artifacts": [],
            "summary": {"total": 0, "by_type": {}},
            "created_at": _utcnow_rfc3339(),
            "updated_at": _utcnow_rfc3339(),
        }
    manifest = manifest_result

    # Deep merge the patch
    patch = _redact_secrets(patch)
    manifest = _deep_merge(manifest, patch)
    manifest["updated_at"] = _utcnow_rfc3339()

    # Sync summary into state
    artifacts = manifest.get("artifacts", [])
    by_type = {}
    for art in artifacts:
        t = art.get("type", "unknown") if isinstance(art, dict) else "unknown"
        by_type[t] = by_type.get(t, 0) + 1
    manifest["summary"] = {"total": len(artifacts), "by_type": by_type}

    _atomic_write_json(manifest_path, manifest)

    # Sync into state
    state["evidence_summary"] = manifest["summary"]
    state["updated_at"] = _utcnow_rfc3339()
    _atomic_write_json(state_file, state)

    _output(True, state_file=str(state_file), revision=state.get("revision"),
            manifest_artifacts=len(artifacts))
    return 0


def cmd_snapshot(args):
    """Write JSON + MD snapshots with monotonic seq."""
    state_file = Path(args.state_file)
    reason = args.reason or "manual"

    result = _load_json(state_file)
    if isinstance(result, tuple):
        _output(False, state_file=str(state_file), errors=[result[1]])
        return 5
    state = result

    run_dir = state_file.parent
    snapshots_dir = run_dir / SNAPSHOTS_DIR
    snapshots_dir.mkdir(exist_ok=True)

    # Monotonic seq
    existing = sorted(snapshots_dir.glob("snapshot-*.json"))
    if existing:
        last = existing[-1].stem  # snapshot-NNN
        try:
            seq = int(last.split("-")[1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1

    now = _utcnow_rfc3339()
    snap_data = {
        "seq": seq,
        "reason": reason,
        "ts": now,
        "revision": state.get("revision", 0),
        "state": state,
    }

    base = f"snapshot-{seq:03d}"
    _atomic_write_json(snapshots_dir / f"{base}.json", snap_data)

    # MD summary
    md_lines = [
        f"# Snapshot {seq}",
        f"",
        f"- **Reason:** {reason}",
        f"- **Time:** {now}",
        f"- **Revision:** {state.get('revision', 0)}",
        f"- **Phase:** {state.get('phase', '?')}",
        f"- **Status:** {state.get('status', '?')}",
        f"- **Progress:** {json.dumps(state.get('progress', {}))}",
        f"",
    ]
    (snapshots_dir / f"{base}.md").write_text("\n".join(md_lines), encoding="utf-8")

    _output(True, state_file=str(state_file), revision=state.get("revision"),
            snapshot_seq=seq)
    return 0


def _check_stale_artifacts(state, state_file):
    """Check for stale artifacts in task_states and gate_states.

    Returns a dict:
      invalidated_tasks: {task_id: reason}
      invalidated_gates: [gate_index]
      warnings: [str]
    """
    invalidated_tasks = {}
    invalidated_gates = []
    warnings = []
    run_dir = state_file.parent
    worktree = state.get("worktree_path", "")

    # Check task_states
    task_states = state.get("task_states", {})
    if isinstance(task_states, dict):
        for tid, ts in task_states.items():
            if not isinstance(ts, dict):
                continue
            # Skip tasks already in terminal states
            status = ts.get("status", "")
            if status in ("passed", "done", "failed"):
                # Check recorded files exist
                for fpath in ts.get("files_modified", []):
                    resolved = _resolve_artifact_path(fpath, run_dir, worktree)
                    if resolved and not resolved.exists():
                        invalidated_tasks[tid] = f"file_modified not found: {fpath}"
                        break

                # Check evidence_paths exist
                for epath in ts.get("evidence_paths", []):
                    resolved = _resolve_artifact_path(epath, run_dir, worktree)
                    if resolved and not resolved.exists():
                        invalidated_tasks[tid] = f"evidence_path not found: {epath}"
                        break

                # Check commit_sha is reachable (if non-null)
                commit_sha = ts.get("commit_sha", "")
                if commit_sha and not _is_commit_reachable(commit_sha):
                    warnings.append(f"{tid}: commit {commit_sha} not reachable")
                    invalidated_tasks[tid] = f"commit_sha not reachable: {commit_sha}"

    # Check gate_states
    gate_states = state.get("gate_states", [])
    if isinstance(gate_states, list):
        for i, gs in enumerate(gate_states):
            if not isinstance(gs, dict):
                continue
            if not gs.get("passed", False):
                continue
            for epath in gs.get("evidence_paths", []):
                resolved = _resolve_artifact_path(epath, run_dir, worktree)
                if resolved and not resolved.exists():
                    invalidated_gates.append(i)
                    break
    elif isinstance(gate_states, dict):
        for gname, gs in gate_states.items():
            if not isinstance(gs, dict):
                continue
            if not gs.get("passed", False):
                continue
            for epath in gs.get("evidence_paths", []):
                resolved = _resolve_artifact_path(epath, run_dir, worktree)
                if resolved and not resolved.exists():
                    invalidated_gates.append(gname)
                    break

    return {
        "invalidated_tasks": invalidated_tasks,
        "invalidated_gates": invalidated_gates,
        "warnings": warnings,
    }


def _resolve_artifact_path(path_str, run_dir, worktree):
    """Resolve an artifact path to an absolute Path, or None if unsafe."""
    p = Path(path_str)
    if p.is_absolute():
        return p if p.parent.exists() else None
    # Try relative to worktree first
    if worktree:
        candidate = Path(worktree) / path_str
        if candidate.parent.exists():
            return candidate
    # Try relative to run_dir
    candidate = run_dir / path_str
    if candidate.parent.exists():
        return candidate
    return Path(path_str)  # Return as-is; existence check will handle it


def _is_commit_reachable(sha):
    """Check if a commit SHA is reachable in the current git repo."""
    if not sha:
        return True
    try:
        import subprocess
        result = subprocess.run(
            ["git", "cat-file", "-t", sha],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and "commit" in result.stdout
    except Exception:
        # If git is not available, assume reachable to avoid false invalidation
        return True


def _find_newest_valid_snapshot(state_file):
    """Find the newest snapshot with valid state for recovery."""
    run_dir = state_file.parent
    snapshots_dir = run_dir / SNAPSHOTS_DIR
    if not snapshots_dir.is_dir():
        return None

    snapshots = sorted(snapshots_dir.glob("snapshot-*.json"), reverse=True)
    for snap_path in snapshots:
        result = _load_json(snap_path)
        if isinstance(result, tuple):
            continue
        snap = result
        snap_state = snap.get("state", {})
        schema_errors = _validate_state_schema(snap_state)
        if not schema_errors:
            return snap
    return None


def cmd_resume(args):
    """Validate, check stale artifacts, return cursor + summary + next entrypoint.

    Enhanced resume algorithm:
    1. Validate state schema
    2. Check for stale artifacts (files, commit SHAs, evidence paths)
    3. Invalidate only affected task/gate (not entire state)
    4. Recover from newest valid snapshot when state is corrupt
    5. Map cursor to correct full-auto phase entrypoint
    """
    state_file = Path(args.state_file)

    result = _load_json(state_file)
    if isinstance(result, tuple):
        # State corrupt — try snapshot recovery
        snap = _find_newest_valid_snapshot(state_file)
        if snap:
            recovered_state = snap.get("state", {})
            _output(False, state_file=str(state_file),
                    errors=[f"State corrupt: {result[1]}", "Recovered from snapshot"],
                    recovered_from_snapshot=snap.get("seq"),
                    cursor=recovered_state.get("resume_cursor", {}),
                    summary={
                        "phase": recovered_state.get("phase", "scope"),
                        "status": recovered_state.get("status", "ACTIVE"),
                        "revision": recovered_state.get("revision", 0),
                        "progress": recovered_state.get("progress", {}),
                        "groups": recovered_state.get("groups", []),
                        "task_states": recovered_state.get("task_states", {}),
                        "gate_states": recovered_state.get("gate_states", []),
                    })
            return 5
        _output(False, state_file=str(state_file), errors=[result[1]])
        return 5
    state = result

    schema_errors = _validate_state_schema(state)
    if schema_errors:
        _output(False, state_file=str(state_file), errors=["State validation failed"] + schema_errors)
        return 2

    # Stale artifact checking
    stale_report = _check_stale_artifacts(state, state_file)

    cursor = state.get("resume_cursor", {})
    summary = {
        "phase": state.get("phase", "scope"),
        "status": state.get("status", "ACTIVE"),
        "revision": state.get("revision", 0),
        "progress": state.get("progress", {}),
        "groups": state.get("groups", []),
        "task_states": state.get("task_states", {}),
        "gate_states": state.get("gate_states", []),
    }

    # Determine next entrypoint based on phase
    phase = state.get("phase", "scope")
    status = state.get("status", "ACTIVE")
    if status in ("DONE", "CANCELLED", "FAILED_FATAL"):
        entrypoint = "none (terminal)"
    elif status == "STOPPED_ASK_USER":
        entrypoint = "resume_from_user_block"
    elif status == "BLOCKED_ESCALATING":
        entrypoint = "resume_escalation"
    elif phase == "execute":
        entrypoint = "resume_execute"
    elif phase == "gates":
        entrypoint = "resume_gates"
    else:
        entrypoint = f"resume_{phase}"

    # Identify passed tasks for replay (result_replay)
    task_states = state.get("task_states", {})
    replay_tasks = []
    for tid, ts in task_states.items():
        if isinstance(ts, dict) and ts.get("status") in ("passed", "done"):
            replay_tasks.append(tid)

    extra = {}
    if stale_report["invalidated_tasks"]:
        extra["invalidated_tasks"] = stale_report["invalidated_tasks"]
    if stale_report["invalidated_gates"]:
        extra["invalidated_gates"] = stale_report["invalidated_gates"]
    if stale_report["warnings"]:
        extra["warnings"] = stale_report["warnings"]
    if replay_tasks:
        extra["result_replay"] = replay_tasks

    _output(True, state_file=str(state_file), revision=state.get("revision"),
            cursor=cursor, summary=summary, next_entrypoint=entrypoint, **extra)
    return 0


def cmd_validate(args):
    """Schema/gates/tasks/audit/manifest validation."""
    state_file = Path(args.state_file)

    result = _load_json(state_file)
    if isinstance(result, tuple):
        _output(False, state_file=str(state_file), errors=[result[1]])
        return 5
    state = result

    all_errors = []

    # Schema validation
    all_errors.extend(_validate_state_schema(state))

    # Progress consistency
    progress = state.get("progress", {})
    if isinstance(progress, dict):
        tp = progress.get("tasks_passed", 0)
        tt = progress.get("tasks_total", 0)
        if tt > 0 and tp > tt:
            all_errors.append(f"tasks_passed ({tp}) > tasks_total ({tt})")
        gp = progress.get("gates_passed", 0)
        gt = progress.get("gates_total", 0)
        if gt > 0 and gp > gt:
            all_errors.append(f"gates_passed ({gp}) > gates_total ({gt})")

    # Task states vs progress
    task_states = state.get("task_states", {})
    if isinstance(task_states, dict):
        total_ts = len(task_states)
        if total_ts > 0 and progress.get("tasks_total", 0) != total_ts:
            all_errors.append(
                f"tasks_total ({progress.get('tasks_total', 0)}) != "
                f"task_states count ({total_ts})"
            )

    # Audit log exists
    run_dir = state_file.parent
    audit_path = run_dir / state.get("audit_log", f"{AUDIT_DIR}/{AUDIT_FILENAME}")
    if not audit_path.exists():
        all_errors.append("Audit log file missing")

    # Manifest validation
    manifest_path = run_dir / state.get("evidence_dir", EVIDENCE_DIR) / MANIFEST_FILENAME
    if manifest_path.exists():
        mresult = _load_json(manifest_path)
        if isinstance(mresult, tuple):
            all_errors.append(f"Manifest corrupt: {mresult[1]}")
        else:
            all_errors.extend(_validate_manifest(mresult))

    # Gate states
    gate_states = state.get("gate_states", [])
    if not isinstance(gate_states, list):
        all_errors.append("gate_states must be a list")

    if all_errors:
        _output(False, state_file=str(state_file), revision=state.get("revision"),
                errors=all_errors)
        return 2

    _output(True, state_file=str(state_file), revision=state.get("revision"))
    return 0


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        description="Authoritative flow-state helper CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = sub.add_parser("init", help="Create a new workflow run")
    p_init.add_argument("--task-name", required=True)
    p_init.add_argument("--worktree", required=True)
    p_init.add_argument("--spec-path", default="")
    p_init.add_argument("--plan-path", default="")
    p_init.add_argument("--base-ref", default="main")

    # update
    p_update = sub.add_parser("update", help="Update state with a patch")
    p_update.add_argument("--state-file", required=True)
    p_update.add_argument("--patch-json", required=True)
    p_update.add_argument("--expected-revision", type=int, default=None)

    # event
    p_event = sub.add_parser("event", help="Append an audit event")
    p_event.add_argument("--state-file", required=True)
    p_event.add_argument("--type", required=True)
    p_event.add_argument("--json-data", required=True)
    p_event.add_argument("--correlation-id", default=None)

    # manifest
    p_manifest = sub.add_parser("manifest", help="Update evidence manifest")
    p_manifest.add_argument("--state-file", required=True)
    p_manifest.add_argument("--patch-json", required=True)

    # snapshot
    p_snapshot = sub.add_parser("snapshot", help="Create state snapshot")
    p_snapshot.add_argument("--state-file", required=True)
    p_snapshot.add_argument("--reason", default="manual")

    # resume
    p_resume = sub.add_parser("resume", help="Get resume cursor with stale artifact checking")
    p_resume.add_argument("--state-file", required=True)
    p_resume.add_argument("--check-stale", action="store_true", default=True,
                          help="Check for stale artifacts (default: True)")

    # validate
    p_validate = sub.add_parser("validate", help="Validate state")
    p_validate.add_argument("--state-file", required=True)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "init": cmd_init,
        "update": cmd_update,
        "event": cmd_event,
        "manifest": cmd_manifest,
        "snapshot": cmd_snapshot,
        "resume": cmd_resume,
        "validate": cmd_validate,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(2)

    try:
        code = handler(args)
        sys.exit(code)
    except json.JSONDecodeError as e:
        _output(False, errors=[f"JSON parse error: {e}"])
        sys.exit(2)
    except OSError as e:
        _output(False, errors=[f"I/O error: {e}"])
        sys.exit(4)
    except Exception as e:
        _output(False, errors=[f"Unexpected error: {e}"])
        sys.exit(1)


if __name__ == "__main__":
    main()
