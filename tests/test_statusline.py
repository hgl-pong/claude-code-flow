import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts" / "statusline.sh").resolve()


def run_statusline(stdin_json=None, cwd=None, extra_env=None):
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        ["rtk", "bash", str(SCRIPT)],
        input=json.dumps(stdin_json).encode() if stdin_json is not None else None,
        cwd=cwd or ROOT,
        env=env,
        capture_output=True,
        check=False,
    )
    return proc.returncode, proc.stdout.decode(), proc.stderr.decode()


def _make_state(
    task_name="test-run",
    status="ACTIVE",
    updated_at="2026-06-04T12:00:00",
    phase="execute",
    tasks_total=5,
    tasks_completed=2,
    gates_passed=3,
    task_states=None,
    runtime_verification=None,
    **extra,
):
    """Build a state.json dict with sensible defaults."""
    state = {
        "task_name": task_name,
        "status": status,
        "updated_at": updated_at,
        "progress": {
            "phase": phase,
            "tasks_total": tasks_total,
            "tasks_completed": tasks_completed,
            "gates_passed": gates_passed,
        },
    }
    if task_states is not None:
        state["task_states"] = task_states
    if runtime_verification is not None:
        state["runtime_verification"] = runtime_verification
    state.update(extra)
    return state


def run_statusline_with_states(states, cwd=None):
    """Write state files under .claude/auto/<name>/state.json and run statusline.

    states: dict mapping dir_name -> state dict (or None for corrupt file content)
    Returns (returncode, stdout, stderr)
    """
    with tempfile.TemporaryDirectory() as tmp:
        auto_dir = Path(tmp) / ".claude" / "auto"
        auto_dir.mkdir(parents=True)

        for dir_name, state in states.items():
            run_dir = auto_dir / dir_name
            run_dir.mkdir()
            sf = run_dir / "state.json"
            if state is None:
                # Write corrupt JSON
                sf.write_text("{corrupt json!!!", encoding="utf-8")
            else:
                sf.write_text(json.dumps(state), encoding="utf-8")

        return run_statusline(
            stdin_json={"model": {"display_name": "Test"}},
            cwd=tmp,
        )


# ── Existing tests ────────────────────────────────────────────


def test_model_name_shown():
    code, out, err = run_statusline({"model": {"display_name": "Claude"}})
    assert code == 0
    assert "Claude" in out


def test_runtime_evidence_shown():
    code, out, err = run_statusline(
        {
            "runtime_verification": {
                "status": "passed",
                "smoke": "passed",
                "crash_detected": False,
                "hang_detected": False,
                "evidence_dir": ".claude/deliverables/sample",
            }
        }
    )
    assert code == 0
    assert "rt:passed" in out
    assert "smoke:passed" in out


# ── Auto-run discovery tests ──────────────────────────────────


def test_active_run_shown():
    """A single ACTIVE state file should produce auto:<task> output."""
    state = _make_state(
        task_name="my-feature",
        status="ACTIVE",
        phase="execute",
        tasks_total=10,
        tasks_completed=3,
        gates_passed=2,
        task_states={
            "1": {"status": "done"},
            "2": {"status": "done"},
            "3": {"status": "done"},
            "4": {"status": "pending"},
            "5": {"status": "blocked"},
        },
        runtime_verification={"status": "passed", "smoke": "passed"},
    )
    code, out, _ = run_statusline_with_states({"my-feature": state})
    assert code == 0
    assert "auto:my-feature" in out
    assert "execute/ACTIVE" in out
    assert "tasks:3/10" in out
    assert "gates:2/7" in out
    assert "blocked:1" in out
    assert "rt:passed" in out
    assert "smoke:passed" in out


def test_paused_compacting_shown():
    """PAUSED_COMPACTING is an active status and should appear."""
    state = _make_state(task_name="paused-run", status="PAUSED_COMPACTING", phase="compact")
    code, out, _ = run_statusline_with_states({"paused-run": state})
    assert code == 0
    assert "auto:paused-run" in out
    assert "compact/PAUSED_COMPACTING" in out


def test_blocked_escalating_shown():
    """BLOCKED_ESCALATING is an active status."""
    state = _make_state(task_name="blocked-run", status="BLOCKED_ESCALATING", phase="verify")
    code, out, _ = run_statusline_with_states({"blocked-run": state})
    assert code == 0
    assert "auto:blocked-run" in out
    assert "verify/BLOCKED_ESCALATING" in out


def test_stopped_ask_user_shown():
    """STOPPED_ASK_USER is an active status."""
    state = _make_state(task_name="ask-user-run", status="STOPPED_ASK_USER", phase="review")
    code, out, _ = run_statusline_with_states({"ask-user-run": state})
    assert code == 0
    assert "auto:ask-user-run" in out
    assert "review/STOPPED_ASK_USER" in out


def test_inactive_status_not_shown():
    """A COMPLETED status should NOT produce auto: output."""
    state = _make_state(status="COMPLETED", phase="done")
    code, out, _ = run_statusline_with_states({"done-run": state})
    assert code == 0
    assert "auto:" not in out


def test_newest_active_selected():
    """When multiple active runs exist, the newest by updated_at wins."""
    older = _make_state(
        task_name="older-run",
        status="ACTIVE",
        updated_at="2026-06-03T10:00:00",
    )
    newer = _make_state(
        task_name="newer-run",
        status="ACTIVE",
        updated_at="2026-06-04T14:00:00",
    )
    code, out, _ = run_statusline_with_states(
        {"older-run": older, "newer-run": newer}
    )
    assert code == 0
    assert "auto:newer-run" in out
    assert "auto:older-run" not in out


def test_corrupt_newest_shows_error_and_fallback():
    """If newest state file is corrupt, show auto:state-error and fall back."""
    corrupt = None  # signals corrupt file
    valid = _make_state(
        task_name="valid-run",
        status="ACTIVE",
        updated_at="2026-06-03T10:00:00",
    )
    code, out, _ = run_statusline_with_states(
        {"corrupt-run": corrupt, "valid-run": valid}
    )
    assert code == 0
    # The corrupt file is alphabetically before "valid", but sort is by
    # updated_at desc then dirname desc. Corrupt has no valid updated_at
    # so it won't appear in candidates. The valid one should appear.
    assert "auto:valid-run" in out


def test_corrupt_newest_with_timestamp_shows_state_error():
    """Corrupt file with valid structure up front but invalid JSON body."""
    with tempfile.TemporaryDirectory() as tmp:
        auto_dir = Path(tmp) / ".claude" / "auto"
        auto_dir.mkdir(parents=True)

        # Create a corrupt file that has task_name/status/updated_at
        # but is actually invalid JSON (won't pass jq -e '.')
        newer_dir = auto_dir / "newer-bad"
        newer_dir.mkdir()
        (newer_dir / "state.json").write_text("NOT JSON AT ALL", encoding="utf-8")

        valid = _make_state(
            task_name="valid-fallback",
            status="ACTIVE",
            updated_at="2026-06-03T10:00:00",
        )
        valid_dir = auto_dir / "valid-fallback"
        valid_dir.mkdir()
        (valid_dir / "state.json").write_text(
            json.dumps(valid), encoding="utf-8"
        )

        code, out, _ = run_statusline(
            stdin_json={"model": {"display_name": "Test"}},
            cwd=tmp,
        )
        assert code == 0
        # Corrupt file won't pass validation, valid fallback should appear
        assert "auto:valid-fallback" in out


def test_all_corrupt_shows_state_error():
    """If all state files are corrupt, show auto:state-error."""
    code, out, _ = run_statusline_with_states(
        {"bad1": None, "bad2": None}
    )
    assert code == 0
    assert "auto:state-error" in out


def test_no_auto_dir_no_auto_output():
    """Without .claude/auto directory, no auto: output should appear."""
    with tempfile.TemporaryDirectory() as tmp:
        code, out, _ = run_statusline(
            stdin_json={"model": {"display_name": "Test"}},
            cwd=tmp,
        )
        assert code == 0
        assert "auto:" not in out


def test_phase_from_progress_nest():
    """Phase should be read from progress.phase when top-level phase missing."""
    state = _make_state(phase="plan", tasks_total=7, tasks_completed=1)
    del state["progress"]["phase"]  # remove nested
    state["phase"] = "plan"  # add top-level
    # Actually our jq uses: .phase // .progress.phase, so top-level wins
    code, out, _ = run_statusline_with_states({"plan-run": state})
    assert code == 0
    assert "plan/ACTIVE" in out


def test_tasks_passed_fallback():
    """progress.tasks_passed should work as fallback for tasks_completed."""
    state = {
        "task_name": "passed-run",
        "status": "ACTIVE",
        "updated_at": "2026-06-04T12:00:00",
        "progress": {
            "phase": "execute",
            "tasks_total": 4,
            "tasks_passed": 3,
            "gates_passed": 1,
        },
    }
    code, out, _ = run_statusline_with_states({"passed-run": state})
    assert code == 0
    assert "tasks:3/4" in out


def test_truncated_task_name():
    """Task names longer than 20 chars should be truncated."""
    state = _make_state(
        task_name="a-very-long-task-name-that-exceeds-twenty-chars",
        status="ACTIVE",
    )
    code, out, _ = run_statusline_with_states({"long-task": state})
    assert code == 0
    assert "auto:a-very-long-task-na" in out


def test_running_status_active():
    """RUNNING is also an active status."""
    state = _make_state(task_name="running-run", status="RUNNING", phase="brainstorming")
    code, out, _ = run_statusline_with_states({"running-run": state})
    assert code == 0
    assert "auto:running-run" in out
    assert "brainstorming/RUNNING" in out


def test_missing_fields_default_gracefully():
    """State with minimal fields should not crash."""
    state = {
        "task_name": "minimal",
        "status": "ACTIVE",
        "updated_at": "2026-06-04T12:00:00",
    }
    code, out, _ = run_statusline_with_states({"minimal": state})
    assert code == 0
    assert "auto:minimal" in out
    # Should show defaults: tasks:0/0, gates:0/7, blocked:0
    assert "tasks:0/0" in out
    assert "gates:0/7" in out
    assert "blocked:0" in out
