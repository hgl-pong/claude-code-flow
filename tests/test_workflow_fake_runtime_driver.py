"""Fake workflow runtime driver end-to-end contract tests.

Tests the complete Dynamic Workflow lifecycle using pure-Python simulations
and fixture-driven state transitions. No live Dynamic Workflow runtime is
required -- these validate contracts, data shapes, invariants, and state
machine behavior at the boundary.

Covers:
- Full-auto phase transitions through all canonical phases
- execute phase interruption at mid-group and mid-review
- Compaction snapshot creation and restore
- Resume cursor mapping to correct entrypoint
- Replay of passed tasks (no re-run)
- Stale artifact invalidation
- Gate retry with evidence accumulation
- Runtime evidence manifest structure
- Hook output adapter behavior (SubagentStart/Stop schemas)
- State updates/events through the script boundary
"""

import importlib.util
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# -- Import flow-state.py (hyphenated filename requires importlib) -------

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "flow-state.py"
_spec = importlib.util.spec_from_file_location("flow_state", str(SCRIPT_PATH))
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)

# -- Import auto-mode-hooks.py -------------------------------------------

HOOKS_PATH = Path(__file__).resolve().parent.parent / "hooks" / "auto-mode" / "auto-mode-hooks.py"
_hooks_spec = importlib.util.spec_from_file_location("auto_mode_hooks", str(HOOKS_PATH))
hooks = importlib.util.module_from_spec(_hooks_spec)
_hooks_spec.loader.exec_module(hooks)

# -- Constants -----------------------------------------------------------

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dynamic_workflow"

CANONICAL_GATES = [
    "gate_1_tasks_executed",
    "gate_2_reviews_passed",
    "gate_3_tests_pass",
    "gate_4_runtime_evidence",
    "gate_5_spec_verified",
    "gate_6_final_review",
    "gate_7_git_clean",
]

VALID_PHASES = (
    "scope", "research", "design", "synthesize_spec", "review_spec",
    "write_plan", "review_plan", "parse_plan", "execute",
    "gates", "finalize",
)

VALID_STATUSES = (
    "ACTIVE", "PAUSED_COMPACTING", "BLOCKED_ESCALATING",
    "DONE", "STOPPED_ASK_USER", "FAILED_FATAL", "CANCELLED",
)

ESCALATION_LADDER = [
    "schema_retry", "self_service_retry", "stronger_model",
    "split_subtask", "enriched_context", "ask_user",
]


# -- Helpers -------------------------------------------------------------


class _ArgNamespace:
    """Simple namespace to mimic argparse result."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeStdin:
    """Fake stdin for hooks that read from sys.stdin."""
    def __init__(self, content):
        self._content = content

    def read(self):
        return self._content

    def strip(self):
        return self._content.strip()


class _FakeCompletedProc:
    """Fake subprocess result."""
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _load_fixture(name):
    path = FIXTURES / name
    assert path.exists(), f"Fixture not found: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _make_valid_state(**overrides):
    """Return a minimal valid state dict with optional overrides."""
    base = {
        "state_schema_version": 1,
        "revision": 0,
        "task_name": "test",
        "safe_task_name": "test",
        "workflow_run_id": "1",
        "phase": "scope",
        "status": "ACTIVE",
        "progress": {
            "tasks_passed": 0,
            "tasks_total": 0,
            "gates_passed": 0,
            "gates_total": 7,
        },
        "groups": [],
        "task_states": {},
        "gate_states": [],
        "runtime_verification": {},
        "git_state": {},
        "resume_cursor": {},
        "audit_log": "audit/events.jsonl",
        "evidence_dir": "evidence",
        "worktree_path": "/tmp/test",
        "base_ref": "main",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    base.update(overrides)
    return base


def _init_run(tmp_path, task_name="driver-test", **init_kwargs):
    """Create an initialized run directory and return (state_file_path_str, state_dict)."""
    auto = tmp_path / ".claude" / "auto"
    auto.mkdir(parents=True, exist_ok=True)

    args = _ArgNamespace(
        task_name=task_name,
        worktree=str(tmp_path),
        spec_path=init_kwargs.get("spec_path", ""),
        plan_path=init_kwargs.get("plan_path", ""),
        base_ref=init_kwargs.get("base_ref", "main"),
    )
    with patch.object(fs, "_find_auto_dir", return_value=auto), \
         patch("builtins.print"):
        code = fs.cmd_init(args)
    assert code == 0

    runs = fs._load_runs(auto / "runs.json")
    state_file = list(runs.values())[0]["state_file"]
    state = json.loads(Path(state_file).read_text())
    return state_file, state


def _update_state(state_file, patch_dict, expected_rev=None):
    """Apply an update to the state file."""
    args = _ArgNamespace(
        state_file=state_file,
        patch_json=json.dumps(patch_dict),
        expected_revision=expected_rev,
    )
    with patch("builtins.print"):
        code = fs.cmd_update(args)
    assert code == 0
    return json.loads(Path(state_file).read_text())


def _append_event(state_file, event_type, data, correlation_id=None):
    """Append an audit event."""
    args = _ArgNamespace(
        state_file=state_file,
        type=event_type,
        json_data=json.dumps(data),
        correlation_id=correlation_id,
    )
    with patch("builtins.print"):
        code = fs.cmd_event(args)
    assert code == 0


def _take_snapshot(state_file, reason="test"):
    """Create a snapshot and return its path."""
    args = _ArgNamespace(state_file=state_file, reason=reason)
    with patch("builtins.print"):
        code = fs.cmd_snapshot(args)
    assert code == 0
    run_dir = Path(state_file).parent
    snaps = sorted((run_dir / "snapshots").glob("snapshot-*.json"))
    assert len(snaps) >= 1
    return snaps[-1]


def _write_fixture_state(td, data):
    """Write a fixture-derived state into a temp dir with audit/evidence dirs."""
    state_file = Path(td) / "state.json"
    audit_dir = Path(td) / "audit"
    audit_dir.mkdir(exist_ok=True)
    (audit_dir / "events.jsonl").write_text("")
    data = dict(data)
    data["audit_log"] = "audit/events.jsonl"
    data["evidence_dir"] = "evidence"
    state_file.write_text(json.dumps(data))
    return str(state_file)


# ========================================================================
# 1. Full-auto phase transition simulation
# ========================================================================


class TestFullAutoPhaseTransition:
    """Simulate a complete full-auto pipeline through all phases using flow-state."""

    def test_scope_to_done_lifecycle(self, tmp_path, capsys):
        """Drive a state through all phases: scope -> research -> ... -> finalize."""
        state_file, state = _init_run(tmp_path, task_name="lifecycle-test")
        assert state["phase"] == "scope"
        assert state["status"] == "ACTIVE"

        # Phase: scope -> research
        _append_event(state_file, "phase_start", {"phase": "scope"})
        state = _update_state(state_file, {"phase": "research"})
        assert state["phase"] == "research"
        # revision: 0 init, +1 event, +1 update = 2
        assert state["revision"] >= 1

        # Phase: research -> design -> synthesize_spec
        _append_event(state_file, "phase_start", {"phase": "research"})
        state = _update_state(state_file, {
            "phase": "design",
            "design": {
                "design_applicable": False,
                "status": "skipped",
                "skip_reason": "Non-UI task: no frontend visual change requested. Design stage skipped to avoid retrofitting UI/UX work.",
            },
        })
        assert state["phase"] == "design"
        assert state["design"]["design_applicable"] is False

        state = _update_state(state_file, {
            "phase": "synthesize_spec",
            "spec_path": ".claude/specs/lifecycle.md",
        })
        assert state["phase"] == "synthesize_spec"
        assert state.get("spec_path") == ".claude/specs/lifecycle.md"

        # Phase: synthesize_spec -> review_spec -> write_plan -> parse_plan
        state = _update_state(state_file, {"phase": "review_spec"})
        state = _update_state(state_file, {"phase": "write_plan"})
        state = _update_state(state_file, {
            "phase": "parse_plan",
            "plan_path": ".claude/plans/lifecycle.md",
        })
        assert state.get("plan_path") == ".claude/plans/lifecycle.md"

        # Phase: parse_plan -> execute
        state = _update_state(state_file, {
            "phase": "execute",
            "progress": {"tasks_passed": 0, "tasks_total": 3, "gates_passed": 0, "gates_total": 7},
            "groups": [["task-1"], ["task-2", "task-3"]],
            "task_states": {
                "task-1": {"status": "queued", "attempts": 0},
                "task-2": {"status": "queued", "attempts": 0},
                "task-3": {"status": "queued", "attempts": 0},
            },
        })
        assert state["phase"] == "execute"
        assert len(state["task_states"]) == 3

        # Execute: mark tasks as passed
        state = _update_state(state_file, {
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "passed", "attempts": 1},
                "task-3": {"status": "passed", "attempts": 1},
            },
            "progress": {"tasks_passed": 3, "tasks_total": 3, "gates_passed": 0, "gates_total": 7},
        })
        assert state["progress"]["tasks_passed"] == 3

        # Phase: execute -> gates
        state = _update_state(state_file, {
            "phase": "gates",
            "gate_states": [
                {"gate": g, "passed": True, "iterations": 1} for g in CANONICAL_GATES
            ],
            "progress": {"tasks_passed": 3, "tasks_total": 3, "gates_passed": 7, "gates_total": 7},
        })
        assert state["progress"]["gates_passed"] == 7

        # Phase: gates -> finalize -> DONE
        state = _update_state(state_file, {"phase": "finalize", "status": "DONE"})
        assert state["status"] == "DONE"

        # Validate the final state
        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_validate(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["ok"] is True

    def test_every_phase_is_valid(self, tmp_path):
        """Every canonical phase can be set on state."""
        state_file, _ = _init_run(tmp_path, task_name="phase-valid")
        for phase in VALID_PHASES:
            state = _update_state(state_file, {"phase": phase})
            assert state["phase"] == phase

    def test_invalid_phase_rejected(self, tmp_path, capsys):
        """Invalid phase values are rejected by update (post-merge validation)."""
        state_file, _ = _init_run(tmp_path, task_name="bad-phase")
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "INVALID_PHASE"}),
            expected_revision=None,
        )
        code = fs.cmd_update(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 2
        assert any("phase" in e.lower() for e in out.get("errors", []))


# ========================================================================
# 2. Execute-plan interruption
# ========================================================================


class TestExecutePlanInterruption:
    """Test interruption of execute-plan at various mid-execution points."""

    def test_interrupted_mid_group_resume_cursor(self, tmp_path, capsys):
        """Interrupt during group 2 execution -- cursor points to task-3."""
        state_file, _ = _init_run(tmp_path, task_name="mid-group")
        _update_state(state_file, {
            "phase": "execute",
            "progress": {"tasks_passed": 2, "tasks_total": 5, "gates_passed": 0, "gates_total": 7},
            "groups": [["task-1", "task-2"], ["task-3", "task-4", "task-5"]],
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "passed", "attempts": 1},
                "task-3": {"status": "implementing", "attempts": 1},
                "task-4": {"status": "queued", "attempts": 0},
                "task-5": {"status": "queued", "attempts": 0},
            },
            "resume_cursor": {
                "phase": "execute",
                "group_index": 1,
                "completed_groups": 1,
                "task_cursor": "task-3",
            },
        })

        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["next_entrypoint"] == "resume_execute"
        assert out["cursor"]["group_index"] == 1
        assert out["cursor"]["task_cursor"] == "task-3"

    def test_interrupted_mid_review_resume_cursor(self, tmp_path, capsys):
        """Interrupt during spec review of task-2 -- cursor preserves sub_stage."""
        state_file, _ = _init_run(tmp_path, task_name="mid-review")
        _update_state(state_file, {
            "phase": "execute",
            "progress": {"tasks_passed": 1, "tasks_total": 3, "gates_passed": 0, "gates_total": 7},
            "groups": [["task-1"], ["task-2", "task-3"]],
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "spec_reviewing", "attempts": 1},
                "task-3": {"status": "queued", "attempts": 0},
            },
            "resume_cursor": {
                "phase": "execute",
                "group_index": 1,
                "completed_groups": 0,
                "task_cursor": "task-2",
                "sub_stage": "spec_review",
                "spec_iterations": 2,
            },
        })

        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["next_entrypoint"] == "resume_execute"
        assert out["cursor"]["sub_stage"] == "spec_review"
        assert out["cursor"]["spec_iterations"] == 2

    def test_interrupted_fixture_state_validates(self, capsys):
        """Mid-execute interrupted fixture state validates correctly."""
        data = _load_fixture("state_mid_execute_interrupted.json")
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            sf = _write_fixture_state(td, data)
            args = _ArgNamespace(state_file=sf)
            code = fs.cmd_validate(args)
            out = json.loads(capsys.readouterr().out)
            assert code == 0, f"Validation errors: {out.get('errors', [])}"

    def test_interrupted_mid_review_fixture_validates(self, capsys):
        """Mid-review interrupted fixture state validates correctly."""
        data = _load_fixture("state_mid_review_interrupted.json")
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            sf = _write_fixture_state(td, data)
            args = _ArgNamespace(state_file=sf)
            code = fs.cmd_validate(args)
            out = json.loads(capsys.readouterr().out)
            assert code == 0, f"Validation errors: {out.get('errors', [])}"


# ========================================================================
# 3. Compaction snapshot creation and restore
# ========================================================================


class TestCompactionSnapshot:
    """Test snapshot creation during PAUSED_COMPACTING and state restoration."""

    def test_snapshot_captures_full_state(self, tmp_path):
        """Snapshot JSON contains the complete state at the time of capture."""
        state_file, _ = _init_run(tmp_path, task_name="compact-test")
        _update_state(state_file, {
            "phase": "execute",
            "status": "PAUSED_COMPACTING",
            "progress": {"tasks_passed": 2, "tasks_total": 4, "gates_passed": 0, "gates_total": 7},
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "passed", "attempts": 1},
                "task-3": {"status": "implementing", "attempts": 1},
                "task-4": {"status": "queued", "attempts": 0},
            },
        })

        snap_path = _take_snapshot(state_file, reason="compaction")
        snap_data = json.loads(snap_path.read_text())

        assert snap_data["seq"] == 1
        assert snap_data["reason"] == "compaction"
        assert snap_data["state"]["phase"] == "execute"
        assert snap_data["state"]["status"] == "PAUSED_COMPACTING"
        assert len(snap_data["state"]["task_states"]) == 4
        assert snap_data["state"]["progress"]["tasks_passed"] == 2

    def test_snapshot_md_summary_exists(self, tmp_path):
        """Snapshot creates both .json and .md files."""
        state_file, _ = _init_run(tmp_path, task_name="compact-md")
        snap_path = _take_snapshot(state_file, reason="test")
        md_path = snap_path.with_suffix(".md")
        assert md_path.exists()
        md_content = md_path.read_text()
        assert "test" in md_content
        assert "Revision:" in md_content

    def test_snapshot_can_restore_state(self, tmp_path):
        """State can be restored from a snapshot."""
        state_file, _ = _init_run(tmp_path, task_name="restore-test")
        _update_state(state_file, {
            "phase": "execute",
            "status": "PAUSED_COMPACTING",
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "blocked", "attempts": 2},
            },
        })

        snap_path = _take_snapshot(state_file, reason="pre-compaction")
        snap_data = json.loads(snap_path.read_text())

        # Simulate more state changes after snapshot
        _update_state(state_file, {
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "passed", "attempts": 3},
            },
        })

        # Restore from snapshot data
        restored = snap_data["state"]
        assert restored["task_states"]["task-2"]["status"] == "blocked"
        assert restored["task_states"]["task-2"]["attempts"] == 2

    def test_multiple_snapshots_monotonic_seq(self, tmp_path):
        """Multiple snapshots get monotonically increasing sequence numbers."""
        state_file, _ = _init_run(tmp_path, task_name="multi-snap")
        for i in range(4):
            snap = _take_snapshot(state_file, reason=f"snap-{i}")
            data = json.loads(snap.read_text())
            assert data["seq"] == i + 1

    def test_compaction_fixture_snapshot_shape(self):
        """PAUSED_COMPACTING fixture produces valid snapshot data shape."""
        data = _load_fixture("state_paused_compacting.json")
        assert data["status"] == "PAUSED_COMPACTING"
        assert data["phase"] == "execute"

        snap = {
            "seq": 1,
            "reason": "compaction",
            "ts": "2026-06-01T04:00:00Z",
            "revision": data["revision"],
            "state": data,
        }
        assert snap["state"]["task_states"]["task-6"]["status"] == "blocked"
        assert snap["state"]["resume_cursor"]["group_index"] == 1


# ========================================================================
# 4. Resume cursor mapping to correct entrypoint
# ========================================================================


class TestResumeCursorMapping:
    """Test that resume cursor maps to the correct entrypoint based on phase/status."""

    def test_execute_phase_maps_to_resume_execute(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-exec")
        _update_state(state_file, {"phase": "execute"})
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["next_entrypoint"] == "resume_execute"

    def test_gates_phase_maps_to_resume_gates(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-gates")
        _update_state(state_file, {"phase": "gates"})
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["next_entrypoint"] == "resume_gates"

    def test_design_phase_maps_to_resume_design(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-design")
        _update_state(state_file, {"phase": "design"})
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["next_entrypoint"] == "resume_design"

    def test_stopped_ask_user_maps_to_resume_from_user_block(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-ask")
        _update_state(state_file, {"status": "STOPPED_ASK_USER"})
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["next_entrypoint"] == "resume_from_user_block"

    def test_blocked_escalating_maps_to_resume_escalation(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-escalate")
        _update_state(state_file, {"status": "BLOCKED_ESCALATING"})
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["next_entrypoint"] == "resume_escalation"

    def test_done_is_terminal(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-done")
        _update_state(state_file, {"status": "DONE"})
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert "terminal" in out["next_entrypoint"]

    def test_failed_fatal_is_terminal(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-fatal")
        _update_state(state_file, {"status": "FAILED_FATAL"})
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert "terminal" in out["next_entrypoint"]

    def test_cancelled_is_terminal(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-cancel")
        _update_state(state_file, {"status": "CANCELLED"})
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert "terminal" in out["next_entrypoint"]

    def test_scope_phase_maps_to_resume_scope(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-scope")
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["next_entrypoint"] == "resume_scope"

    def test_resume_returns_progress_and_task_states(self, tmp_path, capsys):
        state_file, _ = _init_run(tmp_path, task_name="resume-detail")
        _update_state(state_file, {
            "phase": "execute",
            "progress": {"tasks_passed": 2, "tasks_total": 4, "gates_passed": 0, "gates_total": 7},
            "task_states": {
                "task-1": {"status": "passed"},
                "task-2": {"status": "passed"},
                "task-3": {"status": "implementing"},
                "task-4": {"status": "queued"},
            },
        })
        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["summary"]["progress"]["tasks_passed"] == 2
        assert out["summary"]["progress"]["tasks_total"] == 4
        assert len(out["summary"]["task_states"]) == 4

    def test_stopped_ask_user_fixture_resume(self, capsys):
        """STOPPED_ASK_USER fixture maps to resume_from_user_block."""
        data = _load_fixture("state_stopped_ask_user.json")
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            sf = _write_fixture_state(td, data)
            args = _ArgNamespace(state_file=sf)
            fs.cmd_resume(args)
            out = json.loads(capsys.readouterr().out)
            assert out["next_entrypoint"] == "resume_from_user_block"


# ========================================================================
# 5. Replay of passed tasks (no re-run)
# ========================================================================


class TestReplayPassedTasks:
    """Test that passed tasks are identified and not re-run on resume."""

    def test_passed_tasks_not_requeued(self, tmp_path):
        """After resume, passed tasks should remain passed -- not requeued."""
        state_file, _ = _init_run(tmp_path, task_name="replay-test")
        _update_state(state_file, {
            "phase": "execute",
            "progress": {"tasks_passed": 2, "tasks_total": 4, "gates_passed": 0, "gates_total": 7},
            "groups": [["task-1", "task-2"], ["task-3", "task-4"]],
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "passed", "attempts": 1},
                "task-3": {"status": "implementing", "attempts": 1},
                "task-4": {"status": "queued", "attempts": 0},
            },
        })

        state = json.loads(Path(state_file).read_text())
        passed_ids = [
            tid for tid, ts in state["task_states"].items()
            if ts["status"] == "passed"
        ]
        implementing_ids = [
            tid for tid, ts in state["task_states"].items()
            if ts["status"] not in ("passed", "failed", "done")
        ]

        assert set(passed_ids) == {"task-1", "task-2"}
        assert "task-3" in implementing_ids
        assert "task-1" not in implementing_ids
        assert "task-2" not in implementing_ids

    def test_resume_continues_from_interrupted_group(self, tmp_path, capsys):
        """Resume picks up from the interrupted group, skipping completed groups."""
        state_file, _ = _init_run(tmp_path, task_name="replay-group")
        _update_state(state_file, {
            "phase": "execute",
            "progress": {"tasks_passed": 2, "tasks_total": 5, "gates_passed": 0, "gates_total": 7},
            "groups": [["task-1", "task-2"], ["task-3", "task-4", "task-5"]],
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "passed", "attempts": 1},
                "task-3": {"status": "queued", "attempts": 0},
                "task-4": {"status": "queued", "attempts": 0},
                "task-5": {"status": "queued", "attempts": 0},
            },
            "resume_cursor": {
                "phase": "execute",
                "group_index": 1,
                "completed_groups": 1,
            },
        })

        args = _ArgNamespace(state_file=state_file)
        fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["cursor"]["completed_groups"] == 1
        assert out["cursor"]["group_index"] == 1

    def test_all_passed_tasks_preserved_through_snapshot_restore(self, tmp_path):
        """Passed tasks remain passed after snapshot save/restore cycle."""
        state_file, _ = _init_run(tmp_path, task_name="snap-replay")
        _update_state(state_file, {
            "phase": "execute",
            "progress": {"tasks_passed": 3, "tasks_total": 3, "gates_passed": 0, "gates_total": 7},
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "passed", "attempts": 1},
                "task-3": {"status": "passed", "attempts": 1},
            },
        })

        snap_path = _take_snapshot(state_file, reason="all-passed")
        snap = json.loads(snap_path.read_text())

        for tid, ts in snap["state"]["task_states"].items():
            assert ts["status"] == "passed", f"{tid} should be passed, got {ts['status']}"


# ========================================================================
# 6. Stale artifact invalidation
# ========================================================================


class TestStaleArtifactInvalidation:
    """Test detection and invalidation of stale artifacts in the evidence manifest."""

    @staticmethod
    def _is_artifact_stale(artifact, current_commit_shas):
        """An artifact is stale if its commit_sha is not in current set."""
        art_sha = artifact.get("commit_sha", "")
        if not art_sha:
            return False
        return art_sha not in current_commit_shas

    def test_stale_artifact_detected_by_old_commit(self):
        """Artifact with old commit_sha is detected as stale."""
        manifest = _load_fixture("manifest_stale_artifacts.json")
        current_shas = {"abc111", "abc999"}

        stale = [
            a for a in manifest["artifacts"]
            if self._is_artifact_stale(a, current_shas)
        ]
        assert len(stale) == 2
        stale_names = {a["name"] for a in stale}
        assert "task-6-test-output.txt" in stale_names
        assert "stale-smoke-output.txt" in stale_names

    def test_valid_artifact_not_stale(self):
        """Artifact with current commit_sha is not stale."""
        manifest = _load_fixture("manifest_stale_artifacts.json")
        current_shas = {"abc111", "abc666_old", "abc100_old"}

        stale = [
            a for a in manifest["artifacts"]
            if self._is_artifact_stale(a, current_shas)
        ]
        assert len(stale) == 0

    def test_artifacts_without_commit_sha_not_stale_by_commit(self):
        """Artifacts without commit_sha (e.g. specs, plans) are not stale by commit check."""
        manifest = _load_fixture("manifest_with_evidence.json")
        current_shas = {"abc111"}

        stale = [
            a for a in manifest["artifacts"]
            if self._is_artifact_stale(a, current_shas)
        ]
        stale_names = {a["name"] for a in stale}
        assert "spec.md" not in stale_names
        assert "plan.md" not in stale_names
        assert "task-2-test-output.txt" in stale_names

    def test_stale_artifacts_can_be_invalidated(self):
        """Stale artifacts can be removed from manifest, summary is recomputed."""
        manifest = _load_fixture("manifest_stale_artifacts.json")
        current_shas = {"abc111", "abc999"}

        valid = [
            a for a in manifest["artifacts"]
            if not self._is_artifact_stale(a, current_shas)
        ]
        manifest["artifacts"] = valid

        by_type = {}
        for a in valid:
            t = a.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        manifest["summary"] = {"total": len(valid), "by_type": by_type}

        assert manifest["summary"]["total"] == 1
        assert manifest["summary"]["by_type"]["test_result"] == 1

    def test_invalidate_by_task_status(self):
        """Artifacts belonging to blocked/failed tasks should be invalidated."""
        manifest = _load_fixture("manifest_with_evidence.json")
        task_states = {
            "task-1": {"status": "passed"},
            "task-2": {"status": "passed"},
            "task-3": {"status": "blocked"},
        }
        invalid_statuses = {"blocked", "failed", "failed_review"}

        stale_by_task = [
            a for a in manifest["artifacts"]
            if a.get("task_id")
            and task_states.get(a["task_id"], {}).get("status") in invalid_statuses
        ]
        assert len(stale_by_task) == 1
        assert stale_by_task[0]["task_id"] == "task-3"


# ========================================================================
# 7. Gate retry with evidence accumulation
# ========================================================================


class TestGateRetryWithEvidence:
    """Test gate retry behavior and evidence accumulation across retries."""

    def test_failed_gate_retried_with_incrementing_iterations(self, tmp_path):
        """Gate 4 fails, is retried, and iteration count increases."""
        state_file, _ = _init_run(tmp_path, task_name="gate-retry")
        _update_state(state_file, {
            "phase": "gates",
            "progress": {"tasks_passed": 2, "tasks_total": 2, "gates_passed": 3, "gates_total": 7},
            "gate_states": [
                {"gate": "gate_1_tasks_executed", "passed": True, "iterations": 1},
                {"gate": "gate_2_reviews_passed", "passed": True, "iterations": 1},
                {"gate": "gate_3_tests_pass", "passed": True, "iterations": 1},
                {"gate": "gate_4_runtime_evidence", "passed": False, "iterations": 1},
                {"gate": "gate_5_spec_verified", "passed": False, "iterations": 0},
                {"gate": "gate_6_final_review", "passed": False, "iterations": 0},
                {"gate": "gate_7_git_clean", "passed": False, "iterations": 0},
            ],
        })

        state = json.loads(Path(state_file).read_text())
        gate4 = [g for g in state["gate_states"] if g["gate"] == "gate_4_runtime_evidence"][0]
        assert gate4["passed"] is False
        assert gate4["iterations"] == 1

        # Simulate retry: increment iteration
        gate_states = state["gate_states"]
        for g in gate_states:
            if g["gate"] == "gate_4_runtime_evidence":
                g["iterations"] = 2
        _update_state(state_file, {"gate_states": gate_states})

        state = json.loads(Path(state_file).read_text())
        gate4 = [g for g in state["gate_states"] if g["gate"] == "gate_4_runtime_evidence"][0]
        assert gate4["iterations"] == 2

    def test_gate_passes_after_evidence_provided(self, tmp_path):
        """Gate 4 passes after runtime evidence is provided."""
        state_file, _ = _init_run(tmp_path, task_name="gate-evidence")
        _update_state(state_file, {
            "phase": "gates",
            "progress": {"tasks_passed": 2, "tasks_total": 2, "gates_passed": 3, "gates_total": 7},
            "gate_states": [
                {"gate": "gate_1_tasks_executed", "passed": True, "iterations": 1},
                {"gate": "gate_2_reviews_passed", "passed": True, "iterations": 1},
                {"gate": "gate_3_tests_pass", "passed": True, "iterations": 1},
                {"gate": "gate_4_runtime_evidence", "passed": False, "iterations": 2},
                {"gate": "gate_5_spec_verified", "passed": False, "iterations": 0},
                {"gate": "gate_6_final_review", "passed": False, "iterations": 0},
                {"gate": "gate_7_git_clean", "passed": False, "iterations": 0},
            ],
        })

        # Provide runtime evidence, mark gate 4 passed
        _update_state(state_file, {
            "runtime_verification": {
                "status": "passed", "smoke": "passed",
                "crash_detected": False, "hang_detected": False,
            },
            "gate_states": [
                {"gate": "gate_1_tasks_executed", "passed": True, "iterations": 1},
                {"gate": "gate_2_reviews_passed", "passed": True, "iterations": 1},
                {"gate": "gate_3_tests_pass", "passed": True, "iterations": 1},
                {"gate": "gate_4_runtime_evidence", "passed": True, "iterations": 3},
                {"gate": "gate_5_spec_verified", "passed": False, "iterations": 0},
                {"gate": "gate_6_final_review", "passed": False, "iterations": 0},
                {"gate": "gate_7_git_clean", "passed": False, "iterations": 0},
            ],
            "progress": {"tasks_passed": 2, "tasks_total": 2, "gates_passed": 4, "gates_total": 7},
        })

        state = json.loads(Path(state_file).read_text())
        gate4 = [g for g in state["gate_states"] if g["gate"] == "gate_4_runtime_evidence"][0]
        assert gate4["passed"] is True
        assert gate4["iterations"] == 3
        assert state["progress"]["gates_passed"] == 4

    def test_passed_gates_not_rechecked(self, tmp_path):
        """Previously passed gates keep their iteration counts on retry."""
        state_file, _ = _init_run(tmp_path, task_name="gate-no-recheck")
        _update_state(state_file, {
            "phase": "gates",
            "gate_states": [
                {"gate": "gate_1_tasks_executed", "passed": True, "iterations": 1},
                {"gate": "gate_2_reviews_passed", "passed": True, "iterations": 1},
                {"gate": "gate_3_tests_pass", "passed": True, "iterations": 1},
                {"gate": "gate_4_runtime_evidence", "passed": False, "iterations": 2},
                {"gate": "gate_5_spec_verified", "passed": False, "iterations": 0},
                {"gate": "gate_6_final_review", "passed": False, "iterations": 0},
                {"gate": "gate_7_git_clean", "passed": False, "iterations": 0},
            ],
        })

        state = json.loads(Path(state_file).read_text())
        passed_gates = [g for g in state["gate_states"] if g["passed"]]
        assert len(passed_gates) == 3
        for g in passed_gates:
            assert g["iterations"] == 1

    def test_partial_gate_fixture_resume(self, capsys):
        """Partial gate fixture resumes at the correct gate cursor."""
        data = _load_fixture("state_gates_partial.json")
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            sf = _write_fixture_state(td, data)
            args = _ArgNamespace(state_file=sf)
            fs.cmd_resume(args)
            out = json.loads(capsys.readouterr().out)
            assert out["next_entrypoint"] == "resume_gates"
            assert out["cursor"]["gate_cursor"] == 3
            passed_gates = [g for g in out["summary"]["gate_states"] if g.get("passed")]
            assert len(passed_gates) == 3


# ========================================================================
# 8. Runtime evidence manifest structure
# ========================================================================


class TestRuntimeEvidenceManifest:
    """Test the evidence manifest structure and summary computation."""

    def test_manifest_schema_structure(self):
        """Manifest has required schema fields."""
        manifest = _load_fixture("manifest_with_evidence.json")
        assert manifest["schema_version"] == 1
        assert "run_id" in manifest
        assert "artifacts" in manifest
        assert isinstance(manifest["artifacts"], list)
        assert "summary" in manifest
        assert "created_at" in manifest
        assert "updated_at" in manifest

    def test_artifact_required_fields(self):
        """Each artifact has name, type, and status."""
        manifest = _load_fixture("manifest_with_evidence.json")
        for art in manifest["artifacts"]:
            assert "name" in art
            assert "type" in art
            assert "status" in art

    def test_summary_matches_artifacts(self):
        """Summary total and by_type match the artifacts list."""
        manifest = _load_fixture("manifest_with_evidence.json")
        total = manifest["summary"]["total"]
        by_type = manifest["summary"]["by_type"]
        assert total == len(manifest["artifacts"])

        computed = {}
        for art in manifest["artifacts"]:
            t = art.get("type", "unknown")
            computed[t] = computed.get(t, 0) + 1
        assert by_type == computed

    def test_manifest_update_via_flow_state(self, tmp_path, capsys):
        """Manifest can be updated via flow-state manifest command."""
        state_file, _ = _init_run(tmp_path, task_name="manifest-test")

        patch_json = json.dumps({
            "artifacts": [
                {"name": "test-1.txt", "type": "test_result", "status": "passed", "task_id": "task-1"},
                {"name": "smoke.txt", "type": "smoke_test", "status": "passed"},
            ],
        })
        args = _ArgNamespace(state_file=state_file, patch_json=patch_json)
        code = fs.cmd_manifest(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["manifest_artifacts"] == 2

        state = json.loads(Path(state_file).read_text())
        assert state["evidence_summary"]["total"] == 2
        assert state["evidence_summary"]["by_type"]["test_result"] == 1
        assert state["evidence_summary"]["by_type"]["smoke_test"] == 1

    def test_artifact_types_are_valid(self):
        """Artifact types come from known set."""
        valid_types = {
            "test_result", "smoke_test", "spec", "plan",
            "screenshot", "log", "diff", "review", "coverage",
        }
        manifest = _load_fixture("manifest_with_evidence.json")
        for art in manifest["artifacts"]:
            assert art["type"] in valid_types, f"Unknown type: {art['type']}"


# ========================================================================
# 9. State updates and events through the script boundary
# ========================================================================


class TestStateUpdatesAndEvents:
    """Test state updates and audit events through the flow-state.py boundary."""

    def test_optimistic_concurrency_enforced(self, tmp_path, capsys):
        """Concurrent updates with wrong revision are rejected."""
        state_file, _ = _init_run(tmp_path, task_name="concurrency")
        args1 = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "research"}),
            expected_revision=0,
        )
        code1 = fs.cmd_update(args1)
        capsys.readouterr()
        assert code1 == 0

        args2 = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "execute"}),
            expected_revision=0,
        )
        code2 = fs.cmd_update(args2)
        out = json.loads(capsys.readouterr().out)
        assert code2 == 3
        assert "mismatch" in str(out.get("errors", "")).lower()

    def test_deep_merge_preserves_existing_keys(self, tmp_path):
        """Deep merge preserves keys not in the patch."""
        state_file, _ = _init_run(tmp_path, task_name="merge")
        _update_state(state_file, {
            "progress": {"tasks_passed": 3, "tasks_total": 5, "gates_passed": 0, "gates_total": 7},
            "task_states": {
                "task-1": {"status": "passed"},
                "task-2": {"status": "passed"},
            },
        })

        _update_state(state_file, {
            "task_states": {"task-3": {"status": "passed"}},
        })

        state = json.loads(Path(state_file).read_text())
        assert state["progress"]["tasks_passed"] == 3
        assert state["progress"]["tasks_total"] == 5
        assert state["progress"]["gates_total"] == 7

    def test_null_deletes_key(self, tmp_path):
        """Null value in patch deletes the key."""
        state_file, _ = _init_run(tmp_path, task_name="null-del")
        _update_state(state_file, {"placeholder_value": "temporary"})
        state = json.loads(Path(state_file).read_text())
        assert state["placeholder_value"] == "temporary"

        _update_state(state_file, {"placeholder_value": None})
        state = json.loads(Path(state_file).read_text())
        assert "placeholder_value" not in state

    def test_events_appended_to_jsonl(self, tmp_path):
        """Audit events are appended to JSONL file."""
        state_file, _ = _init_run(tmp_path, task_name="events")
        _append_event(state_file, "phase_start", {"phase": "scope"})
        _append_event(state_file, "phase_complete", {"phase": "scope"})
        _append_event(state_file, "phase_start", {"phase": "research"})

        run_dir = Path(state_file).parent
        audit = (run_dir / "audit" / "events.jsonl").read_text()
        lines = [l for l in audit.strip().split("\n") if l]
        assert len(lines) == 4  # 1 init + 3 events

        events = [json.loads(l) for l in lines]
        assert events[1]["type"] == "phase_start"
        assert events[1]["data"]["phase"] == "scope"
        assert events[2]["type"] == "phase_complete"
        assert events[3]["type"] == "phase_start"
        assert events[3]["data"]["phase"] == "research"

    def test_events_have_correlation_ids(self, tmp_path):
        """Events have correlation IDs for tracing."""
        state_file, _ = _init_run(tmp_path, task_name="corr")
        _append_event(state_file, "test", {"key": "val"}, correlation_id="corr-123")

        run_dir = Path(state_file).parent
        audit = (run_dir / "audit" / "events.jsonl").read_text()
        lines = [l for l in audit.strip().split("\n") if l]
        last = json.loads(lines[-1])
        assert last["correlation_id"] == "corr-123"

    def test_secrets_redacted_in_patch(self, tmp_path):
        """Secrets are redacted from patches."""
        state_file, _ = _init_run(tmp_path, task_name="secrets")
        _update_state(state_file, {
            "API_KEY": "super-secret-key",
            "normal_field": "visible",
            "AUTH_TOKEN": "also-secret",
        })

        state = json.loads(Path(state_file).read_text())
        assert state["API_KEY"] == "[REDACTED]"
        assert state["AUTH_TOKEN"] == "[REDACTED]"
        assert state["normal_field"] == "visible"

    def test_revision_monotonically_increases(self, tmp_path):
        """Revision increases with every update."""
        state_file, _ = _init_run(tmp_path, task_name="revision")
        for i in range(5):
            state = json.loads(Path(state_file).read_text())
            assert state["revision"] == i
            _update_state(state_file, {"phase": "execute"})


# ========================================================================
# 10. Hook/output adapter behavior (SubagentStart/Stop schemas)
# ========================================================================


class TestSubagentStartAdapter:
    """Test SubagentStart hook output schema."""

    def test_emit_context_json_schema(self, capsys):
        """emit_context_json produces correct hookSpecificOutput schema."""
        hooks.emit_context_json("test context", "SubagentStart")
        out = json.loads(capsys.readouterr().out)
        assert "hookSpecificOutput" in out
        assert out["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
        assert out["hookSpecificOutput"]["additionalContext"] == "test context"

    def test_subagent_start_includes_auto_mode_context(self, tmp_path, capsys, monkeypatch):
        """SubagentStart hook injects AUTO-MODE-CONTEXT when state is active."""
        state_file, _ = _init_run(tmp_path, task_name="hook-start")
        _update_state(state_file, {"phase": "execute"})

        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr('sys.stdin', io.StringIO('{}'))

        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             pytest.raises(SystemExit) as exc_info:
            hooks.hook_subagent_start()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert "hookSpecificOutput" in out
        assert out["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "AUTO-MODE-CONTEXT" in ctx
        assert "auto-mode pipeline" in ctx
        assert "execute" in ctx


class TestSubagentStopAdapter:
    """Test SubagentStop hook output schema."""

    def test_subagent_stop_blocks_empty_output(self, tmp_path, capsys, monkeypatch):
        """SubagentStop blocks when tracked agent has no output."""
        state_file, _ = _init_run(tmp_path, task_name="hook-stop")
        _update_state(state_file, {
            "phase": "execute",
            "active_agents": [{"agent_id": "agent-123", "role": "implementer", "task_id": "task-1"}],
        })

        monkeypatch.chdir(tmp_path)

        input_data = json.dumps({
            "agent_id": "agent-123",
            "agent_type": "general-purpose",
            "last_assistant_message": "",
        })

        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(input_data)), \
             pytest.raises(SystemExit) as exc_info:
            hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "No output" in out["reason"]

    def test_subagent_stop_blocks_gave_up_language(self, tmp_path, capsys, monkeypatch):
        """SubagentStop blocks when agent uses gave-up language."""
        state_file, _ = _init_run(tmp_path, task_name="hook-gaveup")
        _update_state(state_file, {
            "phase": "execute",
            "active_agents": [{"agent_id": "agent-456", "role": "implementer", "task_id": "task-1"}],
        })

        monkeypatch.chdir(tmp_path)

        input_data = json.dumps({
            "agent_id": "agent-456",
            "agent_type": "general-purpose",
            "last_assistant_message": "I cannot proceed without more information.",
        })

        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(input_data)), \
             pytest.raises(SystemExit) as exc_info:
            hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "stuck" in out["reason"].lower() or "auto-mode" in out["reason"].lower()

    def test_subagent_stop_passes_with_valid_output(self, tmp_path, monkeypatch):
        """SubagentStop passes when agent has valid output."""
        state_file, _ = _init_run(tmp_path, task_name="hook-pass")
        _update_state(state_file, {
            "phase": "execute",
            "active_agents": [{"agent_id": "agent-789", "role": "reviewer", "task_id": "task-2"}],
        })

        monkeypatch.chdir(tmp_path)

        input_data = json.dumps({
            "agent_id": "agent-789",
            "agent_type": "general-purpose",
            "last_assistant_message": "Review complete. Found 2 minor issues. Files: a.py, b.py",
        })

        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(input_data)), \
             pytest.raises(SystemExit) as exc_info:
            hooks.hook_subagent_stop()
        assert exc_info.value.code == 0


class TestStopHook:
    """Test main agent Stop hook."""

    def test_stop_blocks_when_auto_mode_active(self, tmp_path, capsys, monkeypatch):
        """Stop hook blocks and generates resume prompt when auto-mode is active."""
        state_file, _ = _init_run(tmp_path, task_name="hook-main-stop")
        _update_state(state_file, {
            "phase": "execute",
            "progress": {"tasks_passed": 1, "tasks_total": 3, "gates_passed": 0, "gates_total": 7},
            # Hooks expect gate_states as a dict (for .items()), not a list
            "gate_states": {
                "gate_1_tasks_executed": {"passed": True, "iterations": 1},
            },
        })

        monkeypatch.chdir(tmp_path)

        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "AUTO-MODE CONTINUATION" in out["reason"]
        assert "execute" in out["reason"]

    def test_stop_passes_when_no_auto_mode(self, monkeypatch):
        """Stop hook passes when no auto-mode is active."""
        monkeypatch.chdir("/tmp")
        with patch.object(hooks, "auto_mode_active", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()
        assert exc_info.value.code == 0


class TestPreCompactHook:
    """Test PreCompact hook writes snapshot."""

    def test_pre_compact_creates_snapshot(self, tmp_path, monkeypatch):
        """PreCompact hook creates a compact-snapshot.md file."""
        state_file, _ = _init_run(tmp_path, task_name="hook-compact")
        _update_state(state_file, {
            "phase": "execute",
            "progress": {"tasks_passed": 2, "tasks_total": 4, "gates_passed": 0, "gates_total": 7},
            # Hooks expect gate_states as a dict (for .items()), not a list
            "gate_states": {},
        })

        monkeypatch.chdir(tmp_path)

        input_data = json.dumps({"trigger": "auto"})

        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(input_data)), \
             patch("subprocess.run", return_value=_FakeCompletedProc(stdout="abc123 feat: test")):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_pre_compact()

        assert exc_info.value.code == 0
        # The hooks code uses state["task_name"] to build the snapshot path
        state = json.loads(Path(state_file).read_text())
        snapshot = tmp_path / ".claude" / "auto" / state["safe_task_name"] / "compact-snapshot.md"
        assert snapshot.exists()
        content = snapshot.read_text()
        assert "execute" in content
        assert "Auto-Mode Compaction Snapshot" in content


# ========================================================================
# 11. Gate drift and canonical gate validation
# ========================================================================


class TestGateDriftDetection:
    """Test detection of gate count drift (six vs seven gates)."""

    def test_six_gate_fixture_rejected(self):
        """Six-gate fixture must be detected as incomplete."""
        data = _load_fixture("gate_drift_six_vs_seven.json")
        reported = set(data["gate_states"].keys())
        canonical = set(CANONICAL_GATES)
        missing = canonical - reported
        assert len(missing) > 0

    def test_seven_gate_fixture_accepted(self):
        """Done fixture with seven gates passes canonical validation."""
        data = _load_fixture("state_blocked_escalating.json")
        gate_names = {g["gate"] for g in data["gate_states"]}
        canonical = set(CANONICAL_GATES)
        assert gate_names == canonical

    def test_validate_gate_set_function(self):
        """validateGateSet logic correctly identifies missing gates."""
        reported = {f"gate_{i+1}_{name}" for i, name in enumerate([
            "tasks_executed", "reviews_passed", "tests_pass",
            "runtime_evidence", "spec_verified", "final_review", "git_clean",
        ])}
        canonical = set(CANONICAL_GATES)
        missing = canonical - reported
        assert len(missing) == 0

        reported_minus_one = reported - {"gate_4_runtime_evidence"}
        missing = canonical - reported_minus_one
        assert "gate_4_runtime_evidence" in missing


# ========================================================================
# 12. Integration: full lifecycle with all operations
# ========================================================================


class TestFullLifecycleIntegration:
    """End-to-end integration: init, all phases, events, snapshots, manifest, validate."""

    def test_complete_run_lifecycle(self, tmp_path, capsys):
        """Simulate a complete run from init to DONE with all operations."""
        state_file, state = _init_run(tmp_path, task_name="e2e-lifecycle")
        assert state["status"] == "ACTIVE"

        # Phase transitions with events
        for phase in ["research", "design", "synthesize_spec", "write_plan", "parse_plan", "execute"]:
            _append_event(state_file, "phase_start", {"phase": phase})
            patch = {"phase": phase}
            if phase == "design":
                patch["design"] = {
                    "design_applicable": False,
                    "status": "skipped",
                    "skip_reason": "Non-UI task: no frontend visual change requested. Design stage skipped to avoid retrofitting UI/UX work.",
                }
            elif phase == "synthesize_spec":
                patch["spec_path"] = ".claude/specs/e2e.md"
            elif phase == "write_plan":
                patch["plan_path"] = ".claude/plans/e2e.md"
            elif phase == "execute":
                patch.update({
                    "progress": {"tasks_passed": 0, "tasks_total": 2, "gates_passed": 0, "gates_total": 7},
                    "task_states": {
                        "task-1": {"status": "queued", "attempts": 0},
                        "task-2": {"status": "queued", "attempts": 0},
                    },
                })
            _update_state(state_file, patch)

        # Take snapshot mid-execute
        snap = _take_snapshot(state_file, reason="mid-execute")
        snap_data = json.loads(snap.read_text())
        assert snap_data["reason"] == "mid-execute"

        # Complete tasks
        _update_state(state_file, {
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "passed", "attempts": 1},
            },
            "progress": {"tasks_passed": 2, "tasks_total": 2, "gates_passed": 0, "gates_total": 7},
        })

        # Add evidence via manifest
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({
                "artifacts": [
                    {"name": "task-1-output.txt", "type": "test_result", "status": "passed", "task_id": "task-1"},
                    {"name": "task-2-output.txt", "type": "test_result", "status": "passed", "task_id": "task-2"},
                ],
            }),
        )
        fs.cmd_manifest(args)
        capsys.readouterr()

        # Run gates
        _append_event(state_file, "phase_start", {"phase": "gates"})
        _update_state(state_file, {
            "phase": "gates",
            "gate_states": [
                {"gate": g, "passed": True, "iterations": 1} for g in CANONICAL_GATES
            ],
            "progress": {"tasks_passed": 2, "tasks_total": 2, "gates_passed": 7, "gates_total": 7},
        })

        # Finalize
        _append_event(state_file, "run_complete", {"status": "DONE"})
        _update_state(state_file, {"phase": "finalize", "status": "DONE"})

        # Validate final state
        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_validate(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0, f"Validation failed: {out.get('errors', [])}"
        assert out["ok"] is True

        # Verify final state shape
        state = json.loads(Path(state_file).read_text())
        assert state["status"] == "DONE"
        assert state["phase"] == "finalize"
        assert state["progress"]["gates_passed"] == 7
        assert state["progress"]["tasks_passed"] == 2
        assert len(state["gate_states"]) == 7
        assert all(g["passed"] for g in state["gate_states"])

        # Verify audit trail
        run_dir = Path(state_file).parent
        audit = (run_dir / "audit" / "events.jsonl").read_text()
        events = [json.loads(l) for l in audit.strip().split("\n") if l]
        event_types = [e["type"] for e in events]
        assert "run_created" in event_types
        assert event_types.count("phase_start") >= 5
        assert "run_complete" in event_types

        # Verify manifest
        manifest = json.loads((run_dir / "evidence" / "manifest.json").read_text())
        assert manifest["summary"]["total"] == 2
        assert state["evidence_summary"]["total"] == 2

    def test_browser_game_development_lifecycle_requires_design_docs_and_playtest_evidence(self, tmp_path, capsys):
        """Simulate new browser-game work from planning docs through playtest evidence."""
        state_file, state = _init_run(tmp_path, task_name="make-a-2d-browser-game")
        run_dir = Path(state_file).parent

        # Scope/research classify this as new game development, not a narrow bugfix.
        _append_event(state_file, "phase_start", {"phase": "scope", "task_kind": "new_browser_game"})
        state = _update_state(state_file, {
            "phase": "design",
            "design": {
                "design_applicable": True,
                "status": "accepted",
                "classification": "ui_ux_frontend_visual",
                "evidence": ["new playable canvas", "HUD", "controls", "asset presentation"],
                "paths": {"design": "DESIGN.md"},
            },
        })
        assert state["design"]["design_applicable"] is True

        # Spec must call for lightweight game-design docs before implementation.
        spec_path = run_dir / "spec.md"
        spec_path.write_text(
            "\n".join([
                "# Spec: 2D Browser Game",
                "Runtime: prompt-only Phaser + TypeScript + Vite",
                "Required docs: GAME_DESIGN.md, MECHANICS_SPEC.md, CONTENT_PLAN.md, UX_PLAYTEST_PLAN.md, ASSET_BRIEF.md",
                "Acceptance: AC-1 boot route /, AC-2 player moves via semantic input, AC-3 core loop visible, AC-4 screenshot evidence",
            ]),
            encoding="utf-8",
        )
        state = _update_state(state_file, {"phase": "synthesize_spec", "spec_path": str(spec_path)})
        spec_text = spec_path.read_text(encoding="utf-8")
        for doc in ["GAME_DESIGN.md", "MECHANICS_SPEC.md", "CONTENT_PLAN.md", "UX_PLAYTEST_PLAN.md", "ASSET_BRIEF.md"]:
            assert doc in spec_text

        # Plan orders game-design docs before implementation and playtest tasks.
        plan_tasks = {
            "task-1": {
                "status": "queued",
                "subsystem": "game-design",
                "files": ["GAME_DESIGN.md", "MECHANICS_SPEC.md", "CONTENT_PLAN.md", "UX_PLAYTEST_PLAN.md", "ASSET_BRIEF.md"],
                "acceptance_refs": ["AC-1", "AC-2", "AC-3", "AC-4"],
                "runtime_evidence_required": "not_needed",
                "depends_on": [],
            },
            "task-2": {
                "status": "queued",
                "subsystem": "simulation",
                "depends_on": ["task-1"],
                "acceptance_refs": ["AC-2", "AC-3"],
                "runtime_evidence_required": "optional",
            },
            "task-3": {
                "status": "queued",
                "subsystem": "renderer",
                "depends_on": ["task-1", "task-2"],
                "acceptance_refs": ["AC-1", "AC-2", "AC-3"],
                "runtime_evidence_required": "required",
            },
            "task-4": {
                "status": "queued",
                "subsystem": "playtest",
                "depends_on": ["task-3"],
                "acceptance_refs": ["AC-1", "AC-2", "AC-3", "AC-4"],
                "runtime_evidence_required": "required",
            },
        }
        state = _update_state(state_file, {
            "phase": "execute",
            "groups": [["task-1"], ["task-2"], ["task-3"], ["task-4"]],
            "task_states": plan_tasks,
            "progress": {"tasks_passed": 0, "tasks_total": 4, "gates_passed": 0, "gates_total": 7},
        })
        assert state["groups"] == [["task-1"], ["task-2"], ["task-3"], ["task-4"]]
        assert state["task_states"]["task-2"]["depends_on"] == ["task-1"]
        assert state["task_states"]["task-4"]["runtime_evidence_required"] == "required"

        # Simulate completed tasks with runtime artifacts required for visual/browser acceptance.
        for doc in ["GAME_DESIGN.md", "MECHANICS_SPEC.md", "CONTENT_PLAN.md", "UX_PLAYTEST_PLAN.md", "ASSET_BRIEF.md"]:
            (run_dir / doc).write_text(f"# {doc}\nAcceptance-linked game planning.\n", encoding="utf-8")
        _update_state(state_file, {
            "task_states": {tid: {**task, "status": "passed", "attempts": 1} for tid, task in plan_tasks.items()},
            "progress": {"tasks_passed": 4, "tasks_total": 4, "gates_passed": 0, "gates_total": 7},
            "runtime_verification": {
                "status": "passed",
                "route_loaded": "/",
                "render_surface": "canvas",
                "semantic_inputs": ["move_left", "move_right", "jump"],
                "core_loop_observed": True,
                "screenshot": "evidence/game-smoke.png",
                "crash_detected": False,
                "hang_detected": False,
                "unverified_acceptance_items": [],
                "blocking_risks": [],
            },
        })

        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({
                "artifacts": [
                    {"name": "GAME_DESIGN.md", "type": "spec", "status": "passed", "task_id": "task-1"},
                    {"name": "UX_PLAYTEST_PLAN.md", "type": "spec", "status": "passed", "task_id": "task-1"},
                    {"name": "game-smoke.png", "type": "screenshot", "status": "passed", "task_id": "task-4"},
                    {"name": "console.log", "type": "log", "status": "passed", "task_id": "task-4"},
                ],
            }),
        )
        fs.cmd_manifest(args)
        capsys.readouterr()

        # Gates can only pass after game planning docs and browser playtest evidence exist.
        state = json.loads(Path(state_file).read_text())
        assert state["runtime_verification"]["render_surface"] == "canvas"
        assert state["runtime_verification"]["core_loop_observed"] is True
        assert state["runtime_verification"]["unverified_acceptance_items"] == []
        assert state["evidence_summary"]["by_type"]["screenshot"] == 1

        _update_state(state_file, {
            "phase": "gates",
            "gate_states": [{"gate": g, "passed": True, "iterations": 1} for g in CANONICAL_GATES],
            "progress": {"tasks_passed": 4, "tasks_total": 4, "gates_passed": 7, "gates_total": 7},
        })
        state = _update_state(state_file, {"phase": "finalize", "status": "DONE"})
        assert state["status"] == "DONE"

        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_validate(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0, f"Validation failed: {out.get('errors', [])}"
        assert out["ok"] is True
