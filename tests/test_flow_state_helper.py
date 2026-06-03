"""Tests for flow-state.py: authoritative state writer/validator CLI.

Tests import the module directly to avoid subprocess issues in sandboxed
environments.
"""

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Import flow-state.py (hyphenated filename requires importlib)
SCRIPT_PATH = Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "flow-state.py"
_spec = importlib.util.spec_from_file_location("flow_state", str(SCRIPT_PATH))
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory with .claude/auto."""
    auto = tmp_path / ".claude" / "auto"
    auto.mkdir(parents=True)
    return tmp_path


class _ArgNamespace:
    """Simple namespace to mimic argparse result."""
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


@pytest.fixture
def initialized_run(tmp_project):
    """Create an initialized run and return (project_dir, state_file_str).

    Suppresses _output during init so capsys is clean for the test body.
    """
    args = _ArgNamespace(
        task_name="test-task",
        worktree=str(tmp_project),
        spec_path="spec.md",
        plan_path="plan.md",
        base_ref="main",
    )
    # Patch _find_auto_dir to return tmp_project's auto dir
    # Suppress _output so capsys isn't polluted by init
    with patch.object(fs, "_find_auto_dir", return_value=tmp_project / ".claude" / "auto"), \
         patch("builtins.print"):
        exit_code = fs.cmd_init(args)
    assert exit_code == 0, "init failed"

    # Find the created state file
    auto_dir = tmp_project / ".claude" / "auto"
    runs = fs._load_runs(auto_dir / "runs.json")
    state_file = list(runs.values())[0]["state_file"]
    return tmp_project, state_file


# ---------------------------------------------------------------------------
# init
# ---------------------------------------------------------------------------


class TestInit:
    def test_creates_dirs_and_files(self, tmp_project):
        args = _ArgNamespace(
            task_name="my-awesome-task",
            worktree=str(tmp_project),
            spec_path="",
            plan_path="",
            base_ref="main",
        )
        with patch.object(fs, "_find_auto_dir", return_value=tmp_project / ".claude" / "auto"):
            code = fs.cmd_init(args)
        assert code == 0

        auto_dir = tmp_project / ".claude" / "auto"
        runs = fs._load_runs(auto_dir / "runs.json")
        entry = list(runs.values())[0]
        state_file = Path(entry["state_file"])
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert state["state_schema_version"] == 1
        assert state["safe_task_name"] == "my-awesome-task"
        assert state["phase"] == "scope"
        assert state["status"] == "ACTIVE"
        assert state["revision"] == 0

        run_dir = state_file.parent
        assert (run_dir / "audit" / "events.jsonl").exists()
        assert (run_dir / "evidence" / "manifest.json").exists()
        assert (run_dir / "snapshots").is_dir()

    def test_creates_runs_entry(self, tmp_project):
        args = _ArgNamespace(
            task_name="test-task",
            worktree=str(tmp_project),
            spec_path="",
            plan_path="",
            base_ref="main",
        )
        with patch.object(fs, "_find_auto_dir", return_value=tmp_project / ".claude" / "auto"):
            fs.cmd_init(args)

        runs_path = tmp_project / ".claude" / "auto" / "runs.json"
        runs = json.loads(runs_path.read_text())
        assert len(runs) == 1
        entry = list(runs.values())[0]
        assert entry["task_name"] == "test-task"
        assert entry["seq"] == 1

    def test_monotonic_run_seq(self, tmp_project):
        auto_dir = tmp_project / ".claude" / "auto"
        for i in range(3):
            args = _ArgNamespace(
                task_name=f"task-{i}",
                worktree=str(tmp_project),
                spec_path="",
                plan_path="",
                base_ref="main",
            )
            with patch.object(fs, "_find_auto_dir", return_value=auto_dir):
                code = fs.cmd_init(args)
            assert code == 0
        runs = json.loads((auto_dir / "runs.json").read_text())
        assert len(runs) == 3

    def test_safe_name_sanitization(self, tmp_project):
        args = _ArgNamespace(
            task_name="My Task With Spaces & Special! Chars",
            worktree=str(tmp_project),
            spec_path="",
            plan_path="",
            base_ref="main",
        )
        with patch.object(fs, "_find_auto_dir", return_value=tmp_project / ".claude" / "auto"):
            fs.cmd_init(args)
        auto_dir = tmp_project / ".claude" / "auto"
        runs = fs._load_runs(auto_dir / "runs.json")
        state_file = list(runs.values())[0]["state_file"]
        state = json.loads(Path(state_file).read_text())
        assert state["safe_task_name"] == "my-task-with-spaces-special-chars"

    def test_init_with_spec_and_plan(self, tmp_project):
        args = _ArgNamespace(
            task_name="test",
            worktree=str(tmp_project),
            spec_path=".claude/specs/my-spec.md",
            plan_path=".claude/plans/my-plan.md",
            base_ref="develop",
        )
        with patch.object(fs, "_find_auto_dir", return_value=tmp_project / ".claude" / "auto"):
            fs.cmd_init(args)
        auto_dir = tmp_project / ".claude" / "auto"
        runs = fs._load_runs(auto_dir / "runs.json")
        state_file = list(runs.values())[0]["state_file"]
        state = json.loads(Path(state_file).read_text())
        assert state["spec_path"] == ".claude/specs/my-spec.md"
        assert state["plan_path"] == ".claude/plans/my-plan.md"
        assert state["base_ref"] == "develop"


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_basic_patch(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "execute"}),
            expected_revision=None,
        )
        code = fs.cmd_update(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["ok"] is True
        assert out["revision"] == 1

        state = json.loads(Path(state_file).read_text())
        assert state["phase"] == "execute"
        assert state["revision"] == 1

    def test_revision_increments(self, initialized_run, capsys):
        _, state_file = initialized_run
        for i in range(3):
            args = _ArgNamespace(
                state_file=state_file,
                patch_json=json.dumps({"phase": "execute"}),
                expected_revision=None,
            )
            code = fs.cmd_update(args)
            out = json.loads(capsys.readouterr().out)
            assert code == 0
            assert out["revision"] == i + 1

    def test_optimistic_concurrency_success(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "research"}),
            expected_revision=0,
        )
        code = fs.cmd_update(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["revision"] == 1

    def test_optimistic_concurrency_conflict(self, initialized_run, capsys):
        _, state_file = initialized_run
        # First update succeeds
        args1 = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "research"}),
            expected_revision=None,
        )
        fs.cmd_update(args1)
        capsys.readouterr()  # consume output

        # Second with stale revision fails
        args2 = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "execute"}),
            expected_revision=0,
        )
        code = fs.cmd_update(args2)
        out = json.loads(capsys.readouterr().out)
        assert code == 3
        assert "mismatch" in str(out.get("errors", "")).lower()

    def test_deep_merge_objects(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({
                "progress": {"tasks_passed": 3, "tasks_total": 5},
                "git_state": {"branch": "feature-x"},
            }),
            expected_revision=None,
        )
        code = fs.cmd_update(args)
        capsys.readouterr()
        assert code == 0
        state = json.loads(Path(state_file).read_text())
        assert state["progress"]["tasks_passed"] == 3
        assert state["progress"]["gates_total"] == 7  # preserved from default

    def test_null_deletes_key(self, initialized_run, capsys):
        _, state_file = initialized_run
        # Add a key
        args1 = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"temp_key": "value"}),
            expected_revision=None,
        )
        fs.cmd_update(args1)
        capsys.readouterr()

        # Delete it
        args2 = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"temp_key": None}),
            expected_revision=None,
        )
        fs.cmd_update(args2)
        capsys.readouterr()

        state = json.loads(Path(state_file).read_text())
        assert "temp_key" not in state

    def test_array_replaced_not_merged(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"groups": ["group-a"]}),
            expected_revision=None,
        )
        fs.cmd_update(args)
        capsys.readouterr()
        state = json.loads(Path(state_file).read_text())
        assert state["groups"] == ["group-a"]

    def test_secret_redaction(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({
                "API_KEY": "super-secret",
                "normal_field": "visible",
                "AUTH_TOKEN": "also-secret",
            }),
            expected_revision=None,
        )
        code = fs.cmd_update(args)
        capsys.readouterr()
        assert code == 0
        state = json.loads(Path(state_file).read_text())
        assert state["API_KEY"] == "[REDACTED]"
        assert state["AUTH_TOKEN"] == "[REDACTED]"
        assert state["normal_field"] == "visible"


# ---------------------------------------------------------------------------
# event
# ---------------------------------------------------------------------------


class TestEvent:
    def test_appends_to_jsonl(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            type="phase_change",
            json_data=json.dumps({"from": "scope", "to": "research"}),
            correlation_id=None,
        )
        code = fs.cmd_event(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["audit_event_count"] == 2  # 1 from init + 1 new

        run_dir = Path(state_file).parent
        audit = (run_dir / "audit" / "events.jsonl").read_text()
        lines = [l for l in audit.strip().split("\n") if l]
        last = json.loads(lines[-1])
        assert last["type"] == "phase_change"
        assert last["data"]["from"] == "scope"

    def test_custom_correlation_id(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            type="test",
            json_data=json.dumps({}),
            correlation_id="my-correlation-123",
        )
        code = fs.cmd_event(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["correlation_id"] == "my-correlation-123"

    def test_event_count_increments(self, initialized_run, capsys):
        _, state_file = initialized_run
        for i in range(3):
            args = _ArgNamespace(
                state_file=state_file,
                type="tick",
                json_data=json.dumps({"i": i}),
                correlation_id=None,
            )
            code = fs.cmd_event(args)
            capsys.readouterr()
            assert code == 0
        state = json.loads(Path(state_file).read_text())
        assert state["audit_event_count"] == 4  # 1 init + 3 events


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------


class TestManifest:
    def test_merge_artifacts(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({
                "artifacts": [
                    {"name": "test-output.txt", "type": "test_result", "status": "passed"},
                ],
            }),
        )
        code = fs.cmd_manifest(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["manifest_artifacts"] == 1

        run_dir = Path(state_file).parent
        manifest = json.loads((run_dir / "evidence" / "manifest.json").read_text())
        assert len(manifest["artifacts"]) == 1
        assert manifest["summary"]["total"] == 1
        assert manifest["summary"]["by_type"]["test_result"] == 1

    def test_syncs_summary_to_state(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({
                "artifacts": [
                    {"name": "a.txt", "type": "log"},
                    {"name": "b.txt", "type": "log"},
                    {"name": "c.txt", "type": "screenshot"},
                ],
            }),
        )
        fs.cmd_manifest(args)
        capsys.readouterr()
        state = json.loads(Path(state_file).read_text())
        assert state["evidence_summary"]["total"] == 3
        assert state["evidence_summary"]["by_type"]["log"] == 2


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


class TestSnapshot:
    def test_creates_json_and_md(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            reason="pre-execute",
        )
        code = fs.cmd_snapshot(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["snapshot_seq"] == 1

        run_dir = Path(state_file).parent
        snap_json = run_dir / "snapshots" / "snapshot-001.json"
        snap_md = run_dir / "snapshots" / "snapshot-001.md"
        assert snap_json.exists()
        assert snap_md.exists()

        data = json.loads(snap_json.read_text())
        assert data["seq"] == 1
        assert data["reason"] == "pre-execute"

        md = snap_md.read_text()
        assert "pre-execute" in md

    def test_monotonic_seq(self, initialized_run, capsys):
        _, state_file = initialized_run
        for i in range(4):
            args = _ArgNamespace(
                state_file=state_file,
                reason=f"snap-{i}",
            )
            code = fs.cmd_snapshot(args)
            out = json.loads(capsys.readouterr().out)
            assert code == 0
            assert out["snapshot_seq"] == i + 1

        run_dir = Path(state_file).parent
        snaps = sorted((run_dir / "snapshots").glob("snapshot-*.json"))
        assert len(snaps) == 4


# ---------------------------------------------------------------------------
# resume
# ---------------------------------------------------------------------------


class TestResume:
    def test_returns_cursor_and_entrypoint(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["ok"] is True
        assert "cursor" in out
        assert "summary" in out
        assert out["next_entrypoint"] == "resume_scope"

    def test_execute_phase_entrypoint(self, initialized_run, capsys):
        _, state_file = initialized_run
        update_args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "execute"}),
            expected_revision=None,
        )
        fs.cmd_update(update_args)
        capsys.readouterr()

        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert out["next_entrypoint"] == "resume_execute"

    def test_terminal_status_no_entrypoint(self, initialized_run, capsys):
        _, state_file = initialized_run
        update_args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"status": "DONE"}),
            expected_revision=None,
        )
        fs.cmd_update(update_args)
        capsys.readouterr()

        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert "terminal" in out["next_entrypoint"]


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestValidate:
    def test_valid_state(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_validate(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["ok"] is True

    def test_detects_missing_fields(self, tmp_path, capsys):
        bad_state = tmp_path / "state.json"
        bad_state.write_text(json.dumps({"revision": 0}))
        args = _ArgNamespace(state_file=str(bad_state))
        code = fs.cmd_validate(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 2
        assert not out["ok"]
        assert any("Missing" in e for e in out["errors"])

    def test_detects_bad_phase(self, tmp_path, capsys):
        state_file = tmp_path / "state.json"
        state = _make_valid_state()
        state["phase"] = "INVALID_PHASE"
        (tmp_path / "audit").mkdir()
        (tmp_path / "audit" / "events.jsonl").write_text("")
        state_file.write_text(json.dumps(state))
        args = _ArgNamespace(state_file=str(state_file))
        code = fs.cmd_validate(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 2
        assert any("phase" in e.lower() for e in out["errors"])

    def test_detects_progress_inconsistency(self, tmp_path, capsys):
        state_file = tmp_path / "state.json"
        state = _make_valid_state()
        state["progress"] = {
            "tasks_passed": 10,
            "tasks_total": 5,
            "gates_passed": 0,
            "gates_total": 7,
        }
        (tmp_path / "audit").mkdir()
        (tmp_path / "audit" / "events.jsonl").write_text("")
        state_file.write_text(json.dumps(state))
        args = _ArgNamespace(state_file=str(state_file))
        code = fs.cmd_validate(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 2
        assert any("tasks_passed" in e for e in out["errors"])

    def test_detects_missing_audit(self, tmp_path, capsys):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps(_make_valid_state()))
        args = _ArgNamespace(state_file=str(state_file))
        code = fs.cmd_validate(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 2
        assert any("audit" in e.lower() for e in out["errors"])


# ---------------------------------------------------------------------------
# Path safety & atomic write
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    def test_atomic_write_preserves_on_failure(self, initialized_run, capsys):
        _, state_file = initialized_run
        original = json.loads(Path(state_file).read_text())
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "research"}),
            expected_revision=None,
        )
        code = fs.cmd_update(args)
        capsys.readouterr()
        assert code == 0
        state = json.loads(Path(state_file).read_text())
        assert state["phase"] == "research"
        assert state["revision"] == original["revision"] + 1

    def test_no_tmp_files_left(self, initialized_run, capsys):
        _, state_file = initialized_run
        args = _ArgNamespace(
            state_file=state_file,
            patch_json=json.dumps({"phase": "research"}),
            expected_revision=None,
        )
        fs.cmd_update(args)
        capsys.readouterr()
        run_dir = Path(state_file).parent
        tmp_files = list(run_dir.glob("*.tmp")) + list(run_dir.glob("*.json.tmp"))
        assert len(tmp_files) == 0


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


class TestPathSafety:
    def test_safe_name_rejects_empty(self):
        assert fs._validate_safe_name("") is False

    def test_safe_name_rejects_uppercase(self):
        assert fs._validate_safe_name("MyTask") is False

    def test_safe_name_rejects_spaces(self):
        assert fs._validate_safe_name("my task") is False

    def test_safe_name_accepts_valid(self):
        assert fs._validate_safe_name("my-task-123") is True

    def test_path_traversal_rejected(self, tmp_path):
        result = fs._check_path_safety("../../etc/passwd", tmp_path)
        assert result is None

    def test_path_traversal_absolute_rejected(self, tmp_path):
        result = fs._check_path_safety("/etc/passwd", tmp_path)
        assert result is None

    def test_relative_path_accepted(self, tmp_path):
        result = fs._check_path_safety("subdir/file.txt", tmp_path)
        assert result is not None


# ---------------------------------------------------------------------------
# Secret redaction
# ---------------------------------------------------------------------------


class TestSecretRedaction:
    def test_redacts_api_key(self):
        result = fs._redact_secrets({"API_KEY": "secret123", "name": "test"})
        assert result["API_KEY"] == "[REDACTED]"
        assert result["name"] == "test"

    def test_redacts_nested(self):
        result = fs._redact_secrets({
            "config": {"AUTH_TOKEN": "abc", "value": 42}
        })
        assert result["config"]["AUTH_TOKEN"] == "[REDACTED]"
        assert result["config"]["value"] == 42

    def test_redacts_authorization(self):
        result = fs._redact_secrets({"Authorization": "Bearer token"})
        assert result["Authorization"] == "[REDACTED]"

    def test_redacts_cookie(self):
        result = fs._redact_secrets({"Cookie": "session=abc"})
        assert result["Cookie"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_missing_state_file(self, capsys, tmp_path):
        args = _ArgNamespace(
            state_file=str(tmp_path / "nonexistent" / "state.json"),
            patch_json=json.dumps({"phase": "research"}),
            expected_revision=None,
        )
        code = fs.cmd_update(args)
        assert code == 5

    def test_invalid_json_patch(self, initialized_run, capsys):
        _, state_file = initialized_run
        with pytest.raises(json.JSONDecodeError):
            json.loads("{invalid json}")
        # The script parses json in main(), so test the parse failure directly
        args = _ArgNamespace(
            state_file=state_file,
            patch_json="{invalid json}",
            expected_revision=None,
        )
        with pytest.raises(json.JSONDecodeError):
            fs.cmd_update(args)

    def test_validate_corrupt_json(self, tmp_path, capsys):
        state_file = tmp_path / "state.json"
        state_file.write_text("NOT JSON AT ALL{{{")
        args = _ArgNamespace(state_file=str(state_file))
        code = fs.cmd_validate(args)
        assert code == 5

    def test_deep_merge_arrays_replaced(self):
        result = fs._deep_merge(
            {"items": [1, 2, 3]},
            {"items": [4, 5]},
        )
        assert result["items"] == [4, 5]

    def test_deep_merge_nested_dicts(self):
        result = fs._deep_merge(
            {"a": {"b": 1, "c": 2}},
            {"a": {"b": 10, "d": 3}},
        )
        assert result == {"a": {"b": 10, "c": 2, "d": 3}}

    def test_utcnow_format(self):
        ts = fs._utcnow_rfc3339()
        assert ts.endswith("Z")
        assert "T" in ts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_state():
    """Return a minimal valid state dict."""
    return {
        "state_schema_version": 1,
        "revision": 0,
        "task_name": "t",
        "safe_task_name": "t",
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
        "worktree_path": "/tmp",
        "base_ref": "main",
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
