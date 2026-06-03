"""Tests for auto-mode hooks enforcement rules.

Covers:
- Stop: blocks for nonterminal, allows terminal/explicit-user-stop
- SubagentStop: structured output, gave-up language, commit validation, reviewer exemption
- SubagentStart: workflow_run_id, task_id, expected_schema injection
- PreCompact: delegates to flow-state.py snapshot, fallback on failure
- TeammateIdle: blocked/stalled/failed treated as unfinished, terminal top-level exemption
- SessionStart: multi-state discovery and resume/new/list prompt
"""

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# -- Import auto-mode-hooks.py -------------------------------------------

HOOKS_PATH = Path(__file__).resolve().parent.parent / "hooks" / "auto-mode" / "auto-mode-hooks.py"
_hooks_spec = importlib.util.spec_from_file_location("auto_mode_hooks", str(HOOKS_PATH))
hooks = importlib.util.module_from_spec(_hooks_spec)
_hooks_spec.loader.exec_module(hooks)

# -- Import flow-state.py ------------------------------------------------

SCRIPT_PATH = Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "flow-state.py"
_spec = importlib.util.spec_from_file_location("flow_state", str(SCRIPT_PATH))
fs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fs)


# -- Helpers -------------------------------------------------------------


class _ArgNamespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeStdin:
    def __init__(self, content):
        self._content = content

    def read(self):
        return self._content

    def strip(self):
        return self._content.strip()


class _FakeCompletedProc:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _init_run(tmp_path, task_name="enforcement-test"):
    """Create an initialized run and return (project_dir, state_file_str)."""
    auto = tmp_path / ".claude" / "auto"
    auto.mkdir(parents=True, exist_ok=True)

    args = _ArgNamespace(
        task_name=task_name,
        worktree=str(tmp_path),
        spec_path="",
        plan_path="",
        base_ref="main",
    )
    with patch.object(fs, "_find_auto_dir", return_value=auto), \
         patch("builtins.print"):
        code = fs.cmd_init(args)
    assert code == 0

    runs = fs._load_runs(auto / "runs.json")
    state_file = list(runs.values())[0]["state_file"]
    return tmp_path, state_file


def _update_state(state_file, patch_dict):
    args = _ArgNamespace(
        state_file=state_file,
        patch_json=json.dumps(patch_dict),
        expected_revision=None,
    )
    with patch("builtins.print"):
        code = fs.cmd_update(args)
    assert code == 0
    return json.loads(Path(state_file).read_text())


# ========================================================================
# Stop hook enforcement
# ========================================================================


class TestStopEnforcement:
    """Stop hook blocks for nonterminal states, allows terminal/explicit stop."""

    def test_blocks_active_state(self, tmp_path, capsys, monkeypatch):
        """Blocks when status is ACTIVE (nonterminal)."""
        _, state_file = _init_run(tmp_path, task_name="stop-active")
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch.object(hooks, "_call_flow_state_resume", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"

    def test_allows_done_status(self, tmp_path, capsys, monkeypatch):
        """Allows stop when status is DONE (terminal)."""
        _, state_file = _init_run(tmp_path, task_name="stop-done")
        _update_state(state_file, {"status": "DONE"})
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert out == ""  # no block output

    def test_allows_failed_fatal_status(self, tmp_path, capsys, monkeypatch):
        """Allows stop when status is FAILED_FATAL."""
        _, state_file = _init_run(tmp_path, task_name="stop-fatal")
        _update_state(state_file, {"status": "FAILED_FATAL"})
        monkeypatch.chdir(tmp_path)

        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0

    def test_allows_cancelled_status(self, tmp_path, capsys, monkeypatch):
        """Allows stop when status is CANCELLED."""
        _, state_file = _init_run(tmp_path, task_name="stop-cancel")
        _update_state(state_file, {"status": "CANCELLED"})
        monkeypatch.chdir(tmp_path)

        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0

    def test_allows_stopped_ask_user(self, tmp_path, capsys, monkeypatch):
        """Allows stop when status is STOPPED_ASK_USER (explicit user stop)."""
        _, state_file = _init_run(tmp_path, task_name="stop-ask-user")
        _update_state(state_file, {"status": "STOPPED_ASK_USER"})
        monkeypatch.chdir(tmp_path)

        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0

    def test_blocks_paused_compacting(self, tmp_path, capsys, monkeypatch):
        """Blocks when status is PAUSED_COMPACTING (nonterminal)."""
        _, state_file = _init_run(tmp_path, task_name="stop-paused")
        _update_state(state_file, {"status": "PAUSED_COMPACTING"})
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch.object(hooks, "_call_flow_state_resume", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"

    def test_blocks_blocked_escalating(self, tmp_path, capsys, monkeypatch):
        """Blocks when status is BLOCKED_ESCALATING (nonterminal)."""
        _, state_file = _init_run(tmp_path, task_name="stop-blocked")
        _update_state(state_file, {"status": "BLOCKED_ESCALATING"})
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch.object(hooks, "_call_flow_state_resume", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"


# ========================================================================
# SubagentStop enforcement
# ========================================================================


class TestSubagentStopEnforcement:
    """SubagentStop validates structured output, commit, and gave-up language."""

    def _make_input(self, **overrides):
        base = {
            "agent_id": "agent-1",
            "agent_type": "general-purpose",
            "last_assistant_message": "Task completed.",
            "commit_sha": "",
            "expected_files": [],
        }
        base.update(overrides)
        return json.dumps(base)

    def test_blocks_empty_output_implementer(self, tmp_path, capsys, monkeypatch):
        """Blocks implementer with no output."""
        _, state_file = _init_run(tmp_path, task_name="sub-stop-empty")
        _update_state(state_file, {
            "active_agents": [{"agent_id": "agent-1", "role": "implementer"}],
        })
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(self._make_input(last_assistant_message=""))):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "commit" in out["reason"].lower()

    def test_blocks_empty_output_reviewer(self, tmp_path, capsys, monkeypatch):
        """Blocks reviewer with no output."""
        _, state_file = _init_run(tmp_path, task_name="sub-stop-reviewer")
        _update_state(state_file, {
            "active_agents": [{"agent_id": "agent-1", "role": "reviewer"}],
        })
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(self._make_input(
                 last_assistant_message="", agent_type="read-only"
             ))):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "review" in out["reason"].lower()

    def test_blocks_gave_up_language(self, tmp_path, capsys, monkeypatch):
        """Blocks implementer with gave-up language in output."""
        _, state_file = _init_run(tmp_path, task_name="sub-stop-gaveup")
        _update_state(state_file, {
            "active_agents": [{"agent_id": "agent-1", "role": "implementer"}],
        })
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(self._make_input(
                 last_assistant_message="I cannot proceed with this task."
             ))):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "stuck" in out["reason"].lower()

    def test_allows_valid_implementer_with_recent_commit(self, tmp_path, capsys, monkeypatch):
        """Allows implementer with output and recent commit."""
        _, state_file = _init_run(tmp_path, task_name="sub-stop-valid")
        _update_state(state_file, {
            "active_agents": [{"agent_id": "agent-1", "role": "implementer"}],
        })
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(self._make_input())), \
             patch("subprocess.run", return_value=_FakeCompletedProc(stdout="abc123 fix bug\n")):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        # No output = allowed (no block)

    def test_reviewer_exempt_from_commit_requirement(self, tmp_path, capsys, monkeypatch):
        """Reviewer with valid output is allowed even without commit."""
        _, state_file = _init_run(tmp_path, task_name="sub-stop-review")
        _update_state(state_file, {
            "active_agents": [{"agent_id": "agent-1", "role": "reviewer"}],
        })
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(self._make_input(
                 agent_type="read-only",
                 last_assistant_message="Code review findings: no issues.",
                 commit_sha="",
             ))):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert out == ""  # no block

    def test_blocks_unreachable_commit_sha(self, tmp_path, capsys, monkeypatch):
        """Blocks implementer with unreachable commit_sha."""
        _, state_file = _init_run(tmp_path, task_name="sub-stop-unreachable")
        _update_state(state_file, {
            "active_agents": [{"agent_id": "agent-1", "role": "implementer"}],
        })
        monkeypatch.chdir(tmp_path)

        def mock_run(cmd, **kwargs):
            if "cat-file" in cmd:
                return _FakeCompletedProc(returncode=1, stdout="")
            return _FakeCompletedProc(stdout="")

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(self._make_input(
                 commit_sha="deadbeef1234567890",
                 last_assistant_message="Done.",
             ))), \
             patch("subprocess.run", side_effect=mock_run):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "not reachable" in out["reason"]

    def test_blocks_commit_not_touching_expected_files(self, tmp_path, capsys, monkeypatch):
        """Blocks implementer whose commit doesn't touch expected files."""
        _, state_file = _init_run(tmp_path, task_name="sub-stop-files")
        _update_state(state_file, {
            "active_agents": [{"agent_id": "agent-1", "role": "implementer"}],
        })
        monkeypatch.chdir(tmp_path)

        def mock_run(cmd, **kwargs):
            if "cat-file" in cmd:
                return _FakeCompletedProc(returncode=0, stdout="commit\n")
            if "diff-tree" in cmd:
                return _FakeCompletedProc(returncode=0, stdout="other_file.py\n")
            return _FakeCompletedProc(stdout="")

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(self._make_input(
                 commit_sha="abc12345",
                 expected_files=["src/main.py", "src/utils.py"],
                 last_assistant_message="Done implementing.",
             ))), \
             patch("subprocess.run", side_effect=mock_run):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "expected files" in out["reason"].lower()

    def test_allows_commit_touching_expected_files(self, tmp_path, capsys, monkeypatch):
        """Allows implementer whose commit touches expected files."""
        _, state_file = _init_run(tmp_path, task_name="sub-stop-touch")
        _update_state(state_file, {
            "active_agents": [{"agent_id": "agent-1", "role": "implementer"}],
        })
        monkeypatch.chdir(tmp_path)

        def mock_run(cmd, **kwargs):
            if "cat-file" in cmd:
                return _FakeCompletedProc(returncode=0, stdout="commit\n")
            if "diff-tree" in cmd:
                return _FakeCompletedProc(returncode=0, stdout="src/main.py\nsrc/test.py\n")
            return _FakeCompletedProc(stdout="")

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(self._make_input(
                 commit_sha="abc12345",
                 expected_files=["src/main.py"],
                 last_assistant_message="Done implementing.",
             ))), \
             patch("subprocess.run", side_effect=mock_run):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_stop()

        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert out == ""  # no block

    def test_untracked_agent_passes(self, tmp_path, capsys, monkeypatch):
        """Untracked agent passes through without blocking."""
        _, state_file = _init_run(tmp_path, task_name="sub-stop-untracked")
        _update_state(state_file, {
            "active_agents": [{"agent_id": "other-agent", "role": "implementer"}],
        })
        monkeypatch.chdir(tmp_path)

        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(self._make_input(
                 agent_id="untracked-agent",
                 last_assistant_message="",
             ))):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_stop()

        assert exc_info.value.code == 0


# ========================================================================
# SubagentStart enforcement
# ========================================================================


class TestSubagentStartEnforcement:
    """SubagentStart attaches workflow_run_id, task_id, expected_schema."""

    def test_includes_workflow_run_id(self, tmp_path, capsys, monkeypatch):
        """Context includes workflow_run_id from state."""
        _, state_file = _init_run(tmp_path, task_name="sub-start-wrid")
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin("")):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_start()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "workflow_run_id" in ctx

    def test_includes_task_id_from_stdin(self, tmp_path, capsys, monkeypatch):
        """Context includes task_id when provided in stdin."""
        _, state_file = _init_run(tmp_path, task_name="sub-start-tid")
        monkeypatch.chdir(tmp_path)

        stdin_data = json.dumps({"task_id": "task-42", "expected_output_schema": "diff"})
        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(stdin_data)):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_start()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "task-42" in ctx
        assert "expected_output_schema" in ctx

    def test_no_task_id_when_stdin_empty(self, tmp_path, capsys, monkeypatch):
        """Context includes workflow_run_id from state but no task_id when stdin empty."""
        _, state_file = _init_run(tmp_path, task_name="sub-start-nometa")
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin("")):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_start()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        # workflow_run_id is always present from state
        assert "workflow_run_id" in ctx
        # task_id should NOT appear when stdin has no task_id
        assert "task_id:" not in ctx


# ========================================================================
# PreCompact enforcement
# ========================================================================


class TestPreCompactEnforcement:
    """PreCompact delegates to flow-state.py snapshot, reports warnings."""

    def test_calls_flow_state_snapshot(self, tmp_path, capsys, monkeypatch):
        """PreCompact calls flow-state.py snapshot and reports success."""
        _, state_file = _init_run(tmp_path, task_name="compact-snap")
        monkeypatch.chdir(tmp_path)

        snap_output = json.dumps({
            "ok": True,
            "state_file": state_file,
            "revision": 1,
            "snapshot_seq": 1,
        })

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin('{"trigger": "auto"}')), \
             patch.object(hooks, "_call_flow_state_snapshot", return_value=json.loads(snap_output)):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_pre_compact()

        assert exc_info.value.code == 0
        err = capsys.readouterr().err
        assert "snapshot via flow-state.py" in err

    def test_reports_warning_on_snapshot_failure(self, tmp_path, capsys, monkeypatch):
        """PreCompact reports warning when snapshot fails."""
        _, state_file = _init_run(tmp_path, task_name="compact-fail")
        monkeypatch.chdir(tmp_path)

        snap_output = {"ok": False, "errors": ["disk full"]}

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin('{"trigger": "auto"}')), \
             patch.object(hooks, "_call_flow_state_snapshot", return_value=snap_output):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_pre_compact()

        assert exc_info.value.code == 0
        err = capsys.readouterr().err
        assert "WARNING" in err

    def test_fallback_when_flow_state_unavailable(self, tmp_path, capsys, monkeypatch):
        """PreCompact writes fallback snapshot when flow-state.py unavailable."""
        _, state_file = _init_run(tmp_path, task_name="compact-fallback")
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin('{"trigger": "auto"}')), \
             patch.object(hooks, "_call_flow_state_snapshot", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_pre_compact()

        assert exc_info.value.code == 0
        err = capsys.readouterr().err
        assert "WARNING" in err

    def test_no_snapshot_when_no_active_state(self):
        """PreCompact exits immediately when no active state."""
        with patch.object(hooks, "auto_mode_active", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_pre_compact()

        assert exc_info.value.code == 0


# ========================================================================
# TeammateIdle enforcement
# ========================================================================


class TestTeammateIdleEnforcement:
    """TeammateIdle treats blocked/stalled/failed as unfinished."""

    def test_blocks_with_unfinished_tasks(self, tmp_path, capsys, monkeypatch):
        """Blocks when unfinished tasks remain."""
        _, state_file = _init_run(tmp_path, task_name="idle-unfinished")
        _update_state(state_file, {
            "task_states": {
                "task-1": {"status": "implementing"},
                "task-2": {"status": "queued"},
            },
        })
        monkeypatch.chdir(tmp_path)

        stdin_data = json.dumps({"team_name": "my-team", "teammate_name": "worker-1"})
        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(stdin_data)):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_teammate_idle()

        assert exc_info.value.code == 2

    def test_blocks_with_blocked_tasks(self, tmp_path, capsys, monkeypatch):
        """Blocks when blocked tasks exist (treated as unfinished)."""
        _, state_file = _init_run(tmp_path, task_name="idle-blocked")
        _update_state(state_file, {
            "task_states": {
                "task-1": {"status": "blocked"},
            },
        })
        monkeypatch.chdir(tmp_path)

        stdin_data = json.dumps({"team_name": "my-team", "teammate_name": "worker-1"})
        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(stdin_data)):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_teammate_idle()

        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "blocked" in err.lower()

    def test_blocks_with_stalled_tasks(self, tmp_path, capsys, monkeypatch):
        """Blocks when stalled tasks exist."""
        _, state_file = _init_run(tmp_path, task_name="idle-stalled")
        _update_state(state_file, {
            "task_states": {
                "task-1": {"status": "stalled"},
            },
        })
        monkeypatch.chdir(tmp_path)

        stdin_data = json.dumps({"team_name": "my-team", "teammate_name": "worker-1"})
        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(stdin_data)):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_teammate_idle()

        assert exc_info.value.code == 2

    def test_blocks_with_failed_tasks(self, tmp_path, capsys, monkeypatch):
        """Blocks when failed tasks exist (not done/passed)."""
        _, state_file = _init_run(tmp_path, task_name="idle-failed")
        _update_state(state_file, {
            "task_states": {
                "task-1": {"status": "failed"},
            },
        })
        monkeypatch.chdir(tmp_path)

        stdin_data = json.dumps({"team_name": "my-team", "teammate_name": "worker-1"})
        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(stdin_data)):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_teammate_idle()

        assert exc_info.value.code == 2

    def test_allows_when_all_done(self, tmp_path, capsys, monkeypatch):
        """Allows idle when all tasks are done or passed."""
        _, state_file = _init_run(tmp_path, task_name="idle-done")
        _update_state(state_file, {
            "task_states": {
                "task-1": {"status": "done"},
                "task-2": {"status": "passed"},
            },
        })
        monkeypatch.chdir(tmp_path)

        stdin_data = json.dumps({"team_name": "my-team", "teammate_name": "worker-1"})
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(stdin_data)):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_teammate_idle()

        assert exc_info.value.code == 0

    def test_allows_when_top_level_terminal(self, tmp_path, capsys, monkeypatch):
        """Allows idle when top-level status is terminal even with unfinished tasks."""
        _, state_file = _init_run(tmp_path, task_name="idle-terminal")
        _update_state(state_file, {
            "status": "DONE",
            "task_states": {
                "task-1": {"status": "blocked"},
            },
        })
        monkeypatch.chdir(tmp_path)

        stdin_data = json.dumps({"team_name": "my-team", "teammate_name": "worker-1"})
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin(stdin_data)):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_teammate_idle()

        assert exc_info.value.code == 0

    def test_no_team_name_passes(self, tmp_path, monkeypatch):
        """Exits normally when no team_name in input."""
        _, state_file = _init_run(tmp_path, task_name="idle-noteam")
        monkeypatch.chdir(tmp_path)

        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch("sys.stdin", _FakeStdin('{"teammate_name": "worker"}')):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_teammate_idle()

        assert exc_info.value.code == 0

    def test_no_active_state_passes(self):
        """Exits normally when no active state."""
        with patch.object(hooks, "auto_mode_active", return_value=None), \
             patch("sys.stdin", _FakeStdin('{"team_name": "team"}')):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_teammate_idle()

        assert exc_info.value.code == 0


# ========================================================================
# SessionStart multi-state discovery
# ========================================================================


class TestSessionStartEnforcement:
    """SessionStart discovers active states and emits resume/new/list prompt."""

    def test_emits_dangling_for_active_state(self, tmp_path, capsys, monkeypatch):
        """Emits context for a single active state."""
        _, state_file = _init_run(tmp_path, task_name="session-active")
        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch.object(hooks, "discover_active_states", return_value=[
                 {"state_file": state_file, "task_name": "session-active",
                  "phase": "execute", "status": "ACTIVE", "updated_at": "2026-01-01T00:00:00Z",
                  "workflow_run_id": "1"},
             ]):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_session_start()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "AUTO-MODE-DANGLING-TASK" in ctx
        assert "session-active" in ctx

    def test_lists_multiple_active_states(self, tmp_path, capsys, monkeypatch):
        """Lists all active states in the prompt."""
        _, state_file = _init_run(tmp_path, task_name="session-multi")
        monkeypatch.chdir(tmp_path)

        active = [
            {"state_file": "/a/state.json", "task_name": "task-a",
             "phase": "execute", "status": "ACTIVE", "updated_at": "2026-01-02T00:00:00Z",
             "workflow_run_id": "1"},
            {"state_file": "/b/state.json", "task_name": "task-b",
             "phase": "gates", "status": "ACTIVE", "updated_at": "2026-01-01T00:00:00Z",
             "workflow_run_id": "2"},
        ]

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file), \
             patch.object(hooks, "discover_active_states", return_value=active):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_session_start()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "task-a" in ctx
        assert "task-b" in ctx
        assert "2 active task" in ctx

    def test_no_active_states_exits_cleanly(self):
        """Exits normally when no active states found."""
        with patch.object(hooks, "discover_active_states", return_value=[]):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_session_start()

        assert exc_info.value.code == 0


# ========================================================================
# discover_active_states helper
# ========================================================================


class TestDiscoverActiveStates:
    """Test the discover_active_states helper function."""

    def test_discovers_active_states(self, tmp_path, monkeypatch):
        """Finds all nonterminal states."""
        auto = tmp_path / ".claude" / "auto"
        auto.mkdir(parents=True)

        # Create two state files
        for name, status in [("task-a", "ACTIVE"), ("task-b", "DONE")]:
            d = auto / name
            d.mkdir()
            (d / "state.json").write_text(json.dumps({
                "task_name": name, "phase": "execute", "status": status,
                "updated_at": "2026-01-01T00:00:00Z", "workflow_run_id": "1",
            }))

        monkeypatch.chdir(tmp_path)
        states = hooks.discover_active_states()
        assert len(states) == 1
        assert states[0]["task_name"] == "task-a"

    def test_excludes_terminal_states(self, tmp_path, monkeypatch):
        """Excludes DONE, FAILED_FATAL, CANCELLED states."""
        auto = tmp_path / ".claude" / "auto"
        auto.mkdir(parents=True)

        for name, status in [
            ("done", "DONE"), ("fatal", "FAILED_FATAL"), ("cancel", "CANCELLED"),
        ]:
            d = auto / name
            d.mkdir()
            (d / "state.json").write_text(json.dumps({
                "task_name": name, "phase": "scope", "status": status,
                "updated_at": "2026-01-01T00:00:00Z", "workflow_run_id": "1",
            }))

        monkeypatch.chdir(tmp_path)
        states = hooks.discover_active_states()
        assert len(states) == 0


# ========================================================================
# _call_flow_state_snapshot helper
# ========================================================================


class TestCallFlowStateSnapshot:
    """Test the _call_flow_state_snapshot helper."""

    def test_returns_data_on_success(self):
        """Returns parsed JSON when snapshot succeeds."""
        mock_output = json.dumps({"ok": True, "snapshot_seq": 3})
        with patch.object(hooks, "_call_flow_state", return_value=json.loads(mock_output)):
            result = hooks._call_flow_state_snapshot("/some/state.json")
        assert result is not None
        assert result["ok"] is True
        assert result["snapshot_seq"] == 3

    def test_returns_none_on_failure(self):
        """Returns None when snapshot fails."""
        with patch.object(hooks, "_call_flow_state", return_value=None):
            result = hooks._call_flow_state_snapshot("/some/state.json")
        assert result is None
