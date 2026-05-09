"""Tests for scripts/statusline.sh — verifies all rendering scenarios."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "statusline.sh"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _find_bash():
    for candidate in ("bash", "bash.exe", r"C:\Program Files\Git\bin\bash.exe"):
        if shutil.which(candidate):
            return candidate
    raise RuntimeError("bash not found — install Git for Windows or WSL")


BASH = _find_bash()


def run_statusline(stdin_json=None, cwd=None, extra_env=None):
    """Run statusline.sh, optionally piping JSON on stdin. Returns (stdout, stderr)."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [BASH, str(SCRIPT)],
        input=stdin_json.encode() if stdin_json else b"",
        capture_output=True,
        cwd=str(cwd or ROOT),
        env=env,
    )
    return proc.stdout.decode("utf-8", errors="replace"), proc.stderr.decode("utf-8", errors="replace")


def strip_ansi(text):
    return ANSI_RE.sub("", text)


def make_json(**fields):
    """Build a minimal Claude Code statusline JSON payload."""
    base = {
        "model": {"display_name": fields.pop("model", "Sonnet")},
        "workspace": {"current_dir": fields.pop("current_dir", ROOT.as_posix())},
        "context_window": {"used_percentage": fields.pop("ctx_pct", 0)},
        "cost": {"total_cost_usd": fields.pop("cost", 0)},
    }
    if "rate_5h" in fields or "rate_7d" in fields:
        base["rate_limits"] = {}
        if "rate_5h" in fields:
            base["rate_limits"]["five_hour"] = {"used_percentage": fields.pop("rate_5h")}
        if "rate_7d" in fields:
            base["rate_limits"]["seven_day"] = {"used_percentage": fields.pop("rate_7d")}
    for key in ("effort", "thinking", "vim", "agent", "worktree"):
        if key in fields:
            val = fields.pop(key)
            if key == "effort":
                base["effort"] = {"level": val}
            elif key == "thinking":
                base["thinking"] = {"enabled": val}
            elif key == "vim":
                base["vim"] = {"mode": val}
            elif key == "agent":
                base["agent"] = {"name": val}
            elif key == "worktree":
                base.setdefault("workspace", {})["git_worktree"] = val
    base.update(fields)
    return json.dumps(base)


class StatuslineSyntaxTest(unittest.TestCase):
    def test_bash_syntax(self):
        result = subprocess.run([BASH, "-n", str(SCRIPT)], capture_output=True)
        self.assertEqual(result.returncode, 0, f"bash -n failed:\n{result.stderr.decode()}")


class StatuslineJsonParsingTest(unittest.TestCase):
    def test_model_name_shown(self):
        out, _ = run_statusline(make_json(model="Opus 4.7"))
        self.assertIn("Opus 4.7", strip_ansi(out))

    def test_dirname_from_json(self):
        out, _ = run_statusline(make_json(current_dir="/home/user/myproject"))
        self.assertIn("myproject", strip_ansi(out))

    def test_no_stdin_still_renders(self):
        # When no stdin is piped, script should still render (TTY path)
        out, _ = run_statusline(stdin_json=None)
        self.assertGreater(len(strip_ansi(out).strip()), 0)

    def test_empty_json_does_not_crash(self):
        out, _ = run_statusline("{}")
        self.assertGreater(len(strip_ansi(out).strip()), 0)


class StatuslineContextBarTest(unittest.TestCase):
    def test_bar_contains_filled_blocks(self):
        out, _ = run_statusline(make_json(ctx_pct=50))
        self.assertIn("▓", out)

    def test_bar_contains_empty_blocks(self):
        out, _ = run_statusline(make_json(ctx_pct=50))
        self.assertIn("░", out)

    def test_percentage_shown(self):
        out, _ = run_statusline(make_json(ctx_pct=47))
        self.assertIn("47%", strip_ansi(out))

    def test_high_ctx_red_ansi(self):
        out, _ = run_statusline(make_json(ctx_pct=92))
        # Red = \x1b[31m
        self.assertIn("\x1b[31m", out, "high ctx% should use red color")

    def test_low_ctx_green_ansi(self):
        out, _ = run_statusline(make_json(ctx_pct=10))
        self.assertIn("\x1b[32m", out, "low ctx% should use green color")

    def test_medium_ctx_yellow_ansi(self):
        out, _ = run_statusline(make_json(ctx_pct=75))
        # Yellow = \x1b[33m appears at least once (bar color)
        self.assertIn("\x1b[33m", out, "medium ctx% should use yellow color")

    def test_bar_fill_at_92pct(self):
        out, _ = run_statusline(make_json(ctx_pct=92))
        clean = strip_ansi(out)
        # 92% → 9 filled, 1 empty
        self.assertIn("▓▓▓▓▓▓▓▓▓░", clean)


class StatuslineCostTest(unittest.TestCase):
    def test_cost_shown_when_nonzero(self):
        out, _ = run_statusline(make_json(cost=0.456))
        self.assertIn("$0.456", strip_ansi(out))

    def test_cost_hidden_when_zero(self):
        out, _ = run_statusline(make_json(cost=0))
        self.assertNotIn("$", strip_ansi(out))

    def test_cost_three_decimal_places(self):
        out, _ = run_statusline(make_json(cost=0.1))
        self.assertIn("$0.100", strip_ansi(out))


class StatuslineRateLimitsTest(unittest.TestCase):
    def test_five_hour_shown(self):
        out, _ = run_statusline(make_json(rate_5h=72))
        self.assertIn("5h:72%", strip_ansi(out))

    def test_seven_day_shown(self):
        out, _ = run_statusline(make_json(rate_7d=41))
        self.assertIn("7d:41%", strip_ansi(out))

    def test_both_limits_shown(self):
        out, _ = run_statusline(make_json(rate_5h=72, rate_7d=41))
        clean = strip_ansi(out)
        self.assertIn("5h:72%", clean)
        self.assertIn("7d:41%", clean)

    def test_high_limit_red(self):
        out, _ = run_statusline(make_json(rate_5h=85))
        self.assertIn("\x1b[31m", out, "≥80% limit should be red")

    def test_medium_limit_yellow(self):
        out, _ = run_statusline(make_json(rate_5h=65))
        self.assertIn("\x1b[33m", out, "≥60% limit should be yellow")

    def test_absent_limits_hidden(self):
        out, _ = run_statusline(make_json())
        clean = strip_ansi(out)
        self.assertNotIn("5h:", clean)
        self.assertNotIn("7d:", clean)


class StatuslineExtrasTest(unittest.TestCase):
    def test_effort_xhigh_shown(self):
        out, _ = run_statusline(make_json(effort="xhigh"))
        self.assertIn("xhigh", strip_ansi(out))

    def test_effort_high_shown(self):
        out, _ = run_statusline(make_json(effort="high"))
        self.assertIn("high", strip_ansi(out))

    def test_effort_medium_hidden(self):
        out, _ = run_statusline(make_json(effort="medium"))
        self.assertNotIn("medium", strip_ansi(out))

    def test_thinking_emoji_shown(self):
        out, _ = run_statusline(make_json(thinking=True))
        self.assertIn("💭", out)

    def test_thinking_hidden_when_false(self):
        out, _ = run_statusline(make_json(thinking=False))
        self.assertNotIn("💭", out)

    def test_vim_mode_shown(self):
        out, _ = run_statusline(make_json(vim="NORMAL"))
        self.assertIn("NORMAL", strip_ansi(out))

    def test_agent_name_shown(self):
        out, _ = run_statusline(make_json(agent="oracle"))
        self.assertIn("@oracle", strip_ansi(out))

    def test_worktree_shown(self):
        out, _ = run_statusline(make_json(worktree="feat-xyz"))
        self.assertIn("feat-xyz", strip_ansi(out))


class StatuslineFlowStateTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.flow_dir = Path(self._tmp.name) / ".claude" / "flow"
        self.flow_dir.mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, stdin_json=None):
        return run_statusline(stdin_json, cwd=Path(self._tmp.name))

    def test_idle_single_line_with_flow(self):
        out, _ = self._run(make_json())
        lines = [l for l in strip_ansi(out).splitlines() if l.strip()]
        self.assertEqual(len(lines), 1, f"idle should be 1 line, got: {lines}")
        self.assertIn("flow", lines[0])

    def test_active_phase_two_lines(self):
        state = {"phase": "impl", "task_total": 5, "task_done": 3}
        (self.flow_dir / "workflow-state.json").write_text(json.dumps(state))
        out, _ = self._run(make_json())
        lines = [l for l in strip_ansi(out).splitlines() if l.strip()]
        self.assertEqual(len(lines), 2, f"active phase should be 2 lines, got: {lines}")
        self.assertIn("flow:impl", lines[1])
        self.assertIn("3/5", lines[1])

    def test_verification_pass_checkmark(self):
        (self.flow_dir / "last-verification.json").write_text('{"status": "pass"}')
        out, _ = self._run(make_json())
        self.assertIn("✓", out)

    def test_verification_fail_cross(self):
        (self.flow_dir / "last-verification.json").write_text('{"status": "fail"}')
        out, _ = self._run(make_json())
        self.assertIn("✗", out)

    def test_ulw_active_two_lines(self):
        ulw = {"active": True, "intent": "implement", "task_done": 2, "task_total": 7, "iteration": 1}
        (self.flow_dir / "ulw-state.json").write_text(json.dumps(ulw))
        out, _ = self._run(make_json())
        lines = [l for l in strip_ansi(out).splitlines() if l.strip()]
        self.assertEqual(len(lines), 2, f"ULW active should be 2 lines, got: {lines}")
        self.assertIn("⚡ulw:implement", lines[1])
        self.assertIn("2/7", lines[1])
        self.assertIn("#1", lines[1])

    def test_ulw_missing_task_done_defaults_to_zero(self):
        ulw = {"active": True, "intent": "fix", "task_total": 3, "iteration": 0}
        (self.flow_dir / "ulw-state.json").write_text(json.dumps(ulw))
        out, _ = self._run(make_json())
        lines = [l for l in strip_ansi(out).splitlines() if l.strip()]
        line2 = lines[1] if len(lines) > 1 else ""
        self.assertIn("0/3", line2, f"missing task_done should default to 0, got: {line2!r}")
        self.assertNotIn(" /3", line2)

    def test_ulw_inactive_falls_through_to_flow(self):
        (self.flow_dir / "ulw-state.json").write_text('{"active": false}')
        state = {"phase": "review", "task_total": 2, "task_done": 2}
        (self.flow_dir / "workflow-state.json").write_text(json.dumps(state))
        out, _ = self._run(make_json())
        clean = strip_ansi(out)
        self.assertNotIn("⚡ulw", clean)
        self.assertIn("flow:review", clean)


class StatuslineFileIntegrityTest(unittest.TestCase):
    def test_lf_line_endings(self):
        data = SCRIPT.read_bytes()
        crlf_count = data.count(b"\r\n")
        self.assertEqual(crlf_count, 0, f"script has {crlf_count} CRLF line endings (must be LF only)")

    def test_shebang_is_bash(self):
        first_line = SCRIPT.read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(first_line, "#!/bin/bash")


if __name__ == "__main__":
    unittest.main(verbosity=2)
