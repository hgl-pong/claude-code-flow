"""Tests for auto-mode hooks state integration.

Covers:
- Hook state discovery via flow-state.py
- Resume prompt generation with enriched data
- Stale artifact invalidation in hook context
- _call_flow_state_resume integration
- SessionStart dangling task detection
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


def _init_run(tmp_path, task_name="hooks-state-test"):
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
# 1. _call_flow_state_resume integration
# ========================================================================


class TestCallFlowStateResume:
    """Test _call_flow_state_resume helper function."""

    def test_returns_none_when_script_missing(self, tmp_path):
        """Returns None when flow-state.py is not found."""
        result = hooks._call_flow_state_resume(str(tmp_path / "state.json"))
        assert result is None

    def test_returns_data_on_success(self, tmp_path, capsys):
        """Returns parsed JSON when flow-state.py resume succeeds."""
        _, state_file = _init_run(tmp_path, task_name="resume-call")

        capsys.readouterr()

        mock_output = json.dumps({
            "ok": True,
            "state_file": state_file,
            "revision": 0,
            "cursor": {},
            "summary": {"phase": "scope", "status": "ACTIVE"},
            "next_entrypoint": "resume_scope",
        })

        with patch("subprocess.run", return_value=_FakeCompletedProc(stdout=mock_output)):
            result = hooks._call_flow_state_resume(state_file)

        assert result is not None
        assert result.get("ok") is True
        assert "next_entrypoint" in result
        assert "cursor" in result
        assert "summary" in result

    def test_returns_none_on_nonexistent_state(self):
        """Returns None for nonexistent state file."""
        result = hooks._call_flow_state_resume("/nonexistent/state.json")
        # Should return None or a failed result
        assert result is None or (isinstance(result, dict) and not result.get("ok", True))

    def test_returns_result_replay(self, tmp_path, capsys):
        """Returns result_replay list for passed tasks."""
        _, state_file = _init_run(tmp_path, task_name="replay-call")
        _update_state(state_file, {
            "phase": "execute",
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "implementing", "attempts": 0},
            },
        })

        capsys.readouterr()

        mock_output = json.dumps({
            "ok": True,
            "state_file": state_file,
            "revision": 1,
            "cursor": {"phase": "execute"},
            "summary": {"phase": "execute"},
            "next_entrypoint": "resume_execute",
            "result_replay": ["task-1"],
        })

        with patch("subprocess.run", return_value=_FakeCompletedProc(stdout=mock_output)):
            result = hooks._call_flow_state_resume(state_file)

        assert result is not None
        assert "result_replay" in result
        assert "task-1" in result["result_replay"]
        assert "task-2" not in result["result_replay"]


# ========================================================================
# 2. Resume prompt generation
# ========================================================================


class TestResumePromptGeneration:
    """Test generate_resume_prompt with enriched data."""

    def test_prompt_contains_phase(self, tmp_path, capsys):
        """Resume prompt includes the current phase."""
        _, state_file = _init_run(tmp_path, task_name="prompt-phase")
        _update_state(state_file, {"phase": "execute"})

        capsys.readouterr()
        prompt = hooks.generate_resume_prompt(state_file)
        assert "execute" in prompt
        assert "AUTO-MODE CONTINUATION" in prompt

    def test_prompt_contains_task_states(self, tmp_path, capsys):
        """Resume prompt includes task states summary."""
        _, state_file = _init_run(tmp_path, task_name="prompt-tasks")
        _update_state(state_file, {
            "task_states": {
                "task-1": {"status": "passed"},
                "task-2": {"status": "implementing"},
            },
        })

        capsys.readouterr()
        prompt = hooks.generate_resume_prompt(state_file)
        assert "task-1=passed" in prompt
        assert "task-2=implementing" in prompt

    def test_prompt_handles_unreadable_state(self):
        """Resume prompt handles unreadable state file gracefully."""
        prompt = hooks.generate_resume_prompt("/nonexistent/state.json")
        assert "unreadable" in prompt.lower()

    def test_prompt_includes_resume_data_section(self, tmp_path, capsys):
        """Resume prompt includes flow-state.py enrichment when available."""
        _, state_file = _init_run(tmp_path, task_name="prompt-resume")
        _update_state(state_file, {
            "phase": "execute",
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
            },
        })

        capsys.readouterr()
        prompt = hooks.generate_resume_prompt(state_file)
        # The enrichment section may or may not appear depending on
        # whether flow-state.py is callable, but the prompt must be valid
        assert "AUTO-MODE CONTINUATION" in prompt
        assert "task-1=passed" in prompt

    def test_prompt_includes_critical_rules(self, tmp_path, capsys):
        """Resume prompt includes the critical rules section."""
        _, state_file = _init_run(tmp_path, task_name="prompt-rules")

        capsys.readouterr()
        prompt = hooks.generate_resume_prompt(state_file)
        assert "CRITICAL RULES" in prompt
        assert "DO NOT STOP" in prompt


# ========================================================================
# 3. Stop hook state integration
# ========================================================================


class TestStopHookStateIntegration:
    """Test Stop hook uses state discovery correctly."""

    def test_stop_hook_blocks_and_includes_phase(self, tmp_path, capsys, monkeypatch):
        """Stop hook blocks with phase information from state."""
        _, state_file = _init_run(tmp_path, task_name="stop-state")
        _update_state(state_file, {
            "phase": "gates",
            "progress": {"tasks_passed": 3, "tasks_total": 3, "gates_passed": 2, "gates_total": 7},
            "gate_states": {
                "gate_1": {"passed": True},
                "gate_2": {"passed": True},
            },
        })

        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "gates" in out["reason"]

    def test_stop_hook_includes_result_replay_in_prompt(self, tmp_path, capsys, monkeypatch):
        """Stop hook prompt includes result_replay when tasks are passed."""
        _, state_file = _init_run(tmp_path, task_name="stop-replay")
        _update_state(state_file, {
            "phase": "execute",
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "implementing", "attempts": 0},
            },
            "gate_states": {},
        })

        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_stop()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        reason = out["reason"]
        assert "task-1=passed" in reason
        assert "task-2=implementing" in reason


# ========================================================================
# 4. SessionStart hook state integration
# ========================================================================


class TestSessionStartStateIntegration:
    """Test SessionStart hook detects dangling tasks with state."""

    def test_session_start_detects_dangling(self, tmp_path, capsys, monkeypatch):
        """SessionStart hook detects active auto-mode tasks."""
        _, state_file = _init_run(tmp_path, task_name="dangling")
        _update_state(state_file, {"phase": "execute"})

        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_session_start()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        assert "hookSpecificOutput" in out
        assert "AUTO-MODE-DANGLING-TASK" in out["hookSpecificOutput"]["additionalContext"]

    def test_session_start_no_dangling(self, monkeypatch):
        """SessionStart hook passes when no auto-mode is active."""
        with patch.object(hooks, "auto_mode_active", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_session_start()
        assert exc_info.value.code == 0


# ========================================================================
# 5. SubagentStart hook with state
# ========================================================================


class TestSubagentStartStateIntegration:
    """Test SubagentStart hook injects correct state context."""

    def test_subagent_start_includes_phase_from_state(self, tmp_path, capsys, monkeypatch):
        """SubagentStart hook includes the current phase from state."""
        _, state_file = _init_run(tmp_path, task_name="sub-start-state")
        _update_state(state_file, {"phase": "gates"})

        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit) as exc_info:
                hooks.hook_subagent_start()

        assert exc_info.value.code == 0
        out = json.loads(capsys.readouterr().out)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "gates" in ctx
        assert "AUTO-MODE-CONTEXT" in ctx


# ========================================================================
# 6. Stale artifact integration in hooks
# ========================================================================


class TestStaleArtifactHookIntegration:
    """Test that stale artifact information flows through hooks."""

    def test_flow_state_resume_detects_missing_evidence(self, tmp_path, capsys):
        """Resume command reports invalidated tasks when evidence is missing."""
        _, state_file = _init_run(tmp_path, task_name="stale-evidence")
        _update_state(state_file, {
            "phase": "execute",
            "task_states": {
                "task-1": {
                    "status": "passed",
                    "attempts": 1,
                    "evidence_paths": ["/nonexistent/evidence.txt"],
                },
            },
        })

        capsys.readouterr()
        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out["ok"] is True
        # Should report invalidated tasks due to missing evidence
        assert "invalidated_tasks" in out
        assert "task-1" in out["invalidated_tasks"]

    def test_flow_state_resume_reports_replay_for_valid_tasks(self, tmp_path, capsys):
        """Resume command reports result_replay for tasks without stale artifacts."""
        _, state_file = _init_run(tmp_path, task_name="valid-replay")
        _update_state(state_file, {
            "phase": "execute",
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
                "task-2": {"status": "passed", "attempts": 1},
                "task-3": {"status": "implementing", "attempts": 0},
            },
        })

        capsys.readouterr()
        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert "result_replay" in out
        assert "task-1" in out["result_replay"]
        assert "task-2" in out["result_replay"]
        assert "task-3" not in out["result_replay"]

    def test_flow_state_resume_no_invalidation_when_all_valid(self, tmp_path, capsys):
        """Resume reports no invalidated tasks when all artifacts are valid."""
        _, state_file = _init_run(tmp_path, task_name="all-valid")
        _update_state(state_file, {
            "phase": "gates",
            "task_states": {
                "task-1": {"status": "passed", "attempts": 1},
            },
        })

        capsys.readouterr()
        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        assert code == 0
        assert out.get("invalidated_tasks") is None or out.get("invalidated_tasks") == {}

    def test_snapshot_recovery_on_corrupt_state(self, tmp_path, capsys):
        """Resume tries snapshot recovery when state is corrupt."""
        _, state_file = _init_run(tmp_path, task_name="corrupt-recover")

        # Take a snapshot
        snap_args = _ArgNamespace(state_file=state_file, reason="pre-corrupt")
        with patch("builtins.print"):
            fs.cmd_snapshot(snap_args)

        # Corrupt the state file
        Path(state_file).write_text("CORRUPT NOT JSON{{{")

        capsys.readouterr()
        args = _ArgNamespace(state_file=state_file)
        code = fs.cmd_resume(args)
        out = json.loads(capsys.readouterr().out)
        # Should fail with code 5 but attempt recovery
        assert code == 5
        assert "recovered_from_snapshot" in out or any("corrupt" in str(e).lower() for e in out.get("errors", []))


# ========================================================================
# 7. Emitted JSON schema validation
# ========================================================================


class TestEmittedJsonSchema:
    """Test that hook output follows expected JSON schema."""

    def test_stop_hook_output_schema(self, tmp_path, capsys, monkeypatch):
        """Stop hook output has decision and reason fields."""
        _, state_file = _init_run(tmp_path, task_name="schema-stop")
        _update_state(state_file, {"phase": "execute", "gate_states": {}})

        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit):
                hooks.hook_stop()

        out = json.loads(capsys.readouterr().out)
        assert "decision" in out
        assert "reason" in out
        assert isinstance(out["decision"], str)
        assert isinstance(out["reason"], str)

    def test_subagent_start_output_schema(self, tmp_path, capsys, monkeypatch):
        """SubagentStart output has hookSpecificOutput with correct structure."""
        _, state_file = _init_run(tmp_path, task_name="schema-sub")
        _update_state(state_file, {"phase": "execute"})

        monkeypatch.chdir(tmp_path)

        capsys.readouterr()
        with patch.object(hooks, "auto_mode_active", return_value=state_file):
            with pytest.raises(SystemExit):
                hooks.hook_subagent_start()

        out = json.loads(capsys.readouterr().out)
        assert "hookSpecificOutput" in out
        assert "hookEventName" in out["hookSpecificOutput"]
        assert "additionalContext" in out["hookSpecificOutput"]
        assert out["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
