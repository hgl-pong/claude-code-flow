"""Unit tests for ULI hooks (no Claude CLI required).

Covers:
  - uli-detector.py: keyword detection and system prompt injection
  - uli-stop-hook.sh: block/allow exit decisions based on uli-state.json and transcript
    (shell tests are skipped on Windows without bash+jq)
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "hooks" / "scripts"
DETECTOR = str(SCRIPTS / "uli-detector.py")
STOP_HOOK = str(SCRIPTS / "uli-stop-hook.sh")

# Shell tests require bash + jq (unavailable on bare Windows)
BASH_AVAILABLE = shutil.which("bash") is not None and shutil.which("jq") is not None
SKIP_BASH = unittest.skipUnless(
    BASH_AVAILABLE,
    "bash+jq not available — shell hook tests require Git Bash or WSL on Windows"
)


def run_detector(prompt: str) -> tuple:
    """Feed a prompt to uli-detector.py, return (returncode, stdout)."""
    payload = json.dumps({
        "prompt": prompt,
        "session_id": "test-123",
        "hook_event_name": "UserPromptSubmit",
    })
    result = subprocess.run(
        [sys.executable, DETECTOR],
        input=payload,
        text=True,
        capture_output=True,
    )
    return result.returncode, result.stdout.strip()


def make_assistant_line(text: str) -> dict:
    """Build a mock JSONL transcript line as an assistant message."""
    return {
        "role": "assistant",
        "message": {
            "content": [{"type": "text", "text": text}]
        },
    }


def run_stop_hook(state: dict, transcript_lines: list, tmp_dir: str = None) -> tuple:
    """Run uli-stop-hook.sh with given state and transcript, return (returncode, stdout).

    If tmp_dir is provided, state file is written there (so caller can inspect it
    after the hook runs). Otherwise a fresh temp dir is used and cleaned up.
    """
    own_tmp = tmp_dir is None
    if own_tmp:
        tmp_dir = tempfile.mkdtemp()

    try:
        tmp_path = Path(tmp_dir)
        flow_dir = tmp_path / ".claude" / "flow"
        flow_dir.mkdir(parents=True, exist_ok=True)

        state_file = flow_dir / "uli-state.json"
        state_file.write_text(json.dumps(state), encoding="utf-8")

        transcript_file = tmp_path / "transcript.jsonl"
        transcript_file.write_text(
            "\n".join(json.dumps(line) for line in transcript_lines) + "\n",
            encoding="utf-8",
        )

        hook_input = json.dumps({
            "session_id": state.get("session_id", "test-123"),
            "transcript_path": str(transcript_file),
        })

        result = subprocess.run(
            ["bash", STOP_HOOK],
            input=hook_input,
            text=True,
            capture_output=True,
            cwd=tmp_dir,
        )
        return result.returncode, result.stdout.strip()
    finally:
        if own_tmp:
            shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Detector tests (Python — no bash needed)
# ---------------------------------------------------------------------------

class UliDetectorTests(unittest.TestCase):
    """Tests for uli-detector.py keyword detection."""

    def test_uli_keyword_triggers_injection(self):
        code, out = run_detector("uli build me a calculator app")
        self.assertEqual(code, 0)
        self.assertTrue(out, "Expected JSON output when 'uli' detected")
        data = json.loads(out)
        self.assertIn("system_prompt_append", data)
        self.assertIn("ULI", data["system_prompt_append"])
        self.assertTrue(data.get("continue", True))

    def test_uli_case_insensitive(self):
        for prompt in ["ULI add tests", "Uli refactor this", "ulI build a tool"]:
            with self.subTest(prompt=prompt):
                code, out = run_detector(prompt)
                self.assertEqual(code, 0)
                self.assertTrue(out, f"Expected injection for: {prompt}")
                data = json.loads(out)
                self.assertIn("system_prompt_append", data)

    def test_uli_whole_word_only(self):
        """'Julian', 'utility', 'bulletin' must NOT trigger ULI mode."""
        for prompt in ["Julian wrote this", "utility function here", "bulletin board"]:
            with self.subTest(prompt=prompt):
                code, out = run_detector(prompt)
                self.assertEqual(code, 0)
                self.assertEqual(out, "", f"Should NOT trigger for: {prompt}")

    def test_ulw_keyword_does_not_trigger_uli(self):
        """'ulw' should not activate uli-detector (handled by ulw-detector.py)."""
        code, out = run_detector("ulw fix the bug")
        self.assertEqual(code, 0)
        self.assertEqual(out, "", "ulw keyword must not trigger uli-detector")

    def test_no_prompt_exits_silently(self):
        code, out = run_detector("")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_malformed_input_exits_silently(self):
        result = subprocess.run(
            [sys.executable, DETECTOR],
            input="not valid json {{{{",
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_injection_message_contains_loop_description(self):
        """The injected message must explain PD → dev → acceptance loop."""
        _, out = run_detector("uli build something")
        data = json.loads(out)
        msg = data["system_prompt_append"]
        self.assertRegex(msg, r"(?i)(PD|product|iter)", "Should mention PD/product/iteration")
        self.assertRegex(msg, r"(?i)(accept|validat)", "Should mention acceptance")

    def test_uli_at_end_of_sentence(self):
        code, out = run_detector("Please activate uli for this project")
        self.assertEqual(code, 0)
        self.assertTrue(out, "Should trigger when 'uli' appears mid-sentence")


# ---------------------------------------------------------------------------
# Stop hook tests (bash — skipped on Windows without Git Bash / WSL)
# ---------------------------------------------------------------------------

@SKIP_BASH
class UliStopHookTests(unittest.TestCase):
    """Tests for uli-stop-hook.sh block/allow decisions."""

    def _active_state(self, **overrides) -> dict:
        base = {
            "active": True,
            "session_id": "test-123",
            "goal": "build a calculator",
            "iteration": 1,
            "max_iterations": 10,
            "current_phase": "dev_pipeline",
            "current_task_slug": "build-calculator",
            "pd_proposal_ready": True,
            "acceptance_status": None,
            "started_at": "2026-04-30T00:00:00Z",
        }
        base.update(overrides)
        return base

    def test_no_state_file_allows_exit(self):
        """When uli-state.json doesn't exist, hook must exit 0 (allow exit)."""
        with tempfile.TemporaryDirectory() as tmp:
            hook_input = json.dumps({
                "session_id": "test-123",
                "transcript_path": "/dev/null",
            })
            result = subprocess.run(
                ["bash", STOP_HOOK],
                input=hook_input,
                text=True,
                capture_output=True,
                cwd=tmp,
            )
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "")

    def test_active_false_allows_exit(self):
        state = self._active_state(active=False)
        code, out = run_stop_hook(state, [])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_different_session_allows_exit(self):
        state = self._active_state(session_id="other-session")
        code, out = run_stop_hook(state, [make_assistant_line("Working...")])
        self.assertEqual(code, 0)

    def test_uli_done_tag_allows_exit(self):
        state = self._active_state()
        transcript = [make_assistant_line(
            "Done. <uli-done>Built calculator in 2 iterations</uli-done>"
        )]
        code, out = run_stop_hook(state, transcript)
        self.assertEqual(code, 0)
        self.assertIn("complete", out.lower(), "Should confirm completion")

    def test_no_uli_done_tag_blocks_exit(self):
        state = self._active_state()
        transcript = [make_assistant_line("Still working on the implementation...")]
        code, out = run_stop_hook(state, transcript)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data.get("decision"), "block")

    def test_max_iterations_reached_allows_exit(self):
        state = self._active_state(iteration=11, max_iterations=10)
        transcript = [make_assistant_line("Still working...")]
        code, out = run_stop_hook(state, transcript)
        self.assertEqual(code, 0)
        try:
            data = json.loads(out)
            self.assertNotEqual(
                data.get("decision"), "block",
                "Should not block when max iterations reached"
            )
        except json.JSONDecodeError:
            pass  # Non-JSON printed message — that's acceptable

    def test_block_decision_includes_goal(self):
        state = self._active_state(goal="build a REST API")
        transcript = [make_assistant_line("Implementing...")]
        code, out = run_stop_hook(state, transcript)
        data = json.loads(out)
        self.assertEqual(data.get("decision"), "block")
        self.assertIn("REST API", json.dumps(data),
                      "Goal should appear in re-injection message")

    def test_block_decision_mentions_phase(self):
        for phase in ["pd_generating", "dev_pipeline", "acceptance"]:
            with self.subTest(phase=phase):
                state = self._active_state(current_phase=phase)
                transcript = [make_assistant_line("Continuing...")]
                code, out = run_stop_hook(state, transcript)
                data = json.loads(out)
                self.assertEqual(data.get("decision"), "block")
                self.assertIn(phase, json.dumps(data),
                              f"Phase '{phase}' should appear in message")

    def test_uli_state_not_modified_after_block(self):
        """After blocking, uli-state.json must NOT be modified (iteration only advances on ACCEPT)."""
        with tempfile.TemporaryDirectory() as tmp:
            state = self._active_state(iteration=3)
            _code, _out = run_stop_hook(state, [make_assistant_line("Still working...")], tmp_dir=tmp)
            updated = json.loads(
                (Path(tmp) / ".claude" / "flow" / "uli-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(updated["iteration"], 3,
                             "Iteration must NOT increment on block — only advances after acceptance")

    def test_uli_state_marked_inactive_after_done(self):
        """After <uli-done>, uli-state.json should have active=false."""
        with tempfile.TemporaryDirectory() as tmp:
            state = self._active_state()
            transcript = [make_assistant_line(
                "All done. <uli-done>Completed 3 iterations</uli-done>"
            )]
            run_stop_hook(state, transcript, tmp_dir=tmp)
            updated = json.loads(
                (Path(tmp) / ".claude" / "flow" / "uli-state.json").read_text(encoding="utf-8")
            )
            self.assertFalse(updated["active"],
                             "active should be false after <uli-done>")
            self.assertIn("completed_at", updated,
                          "completed_at should be set after <uli-done>")


# ---------------------------------------------------------------------------
# hooks.json registration tests
# ---------------------------------------------------------------------------

class UliHooksJsonRegistrationTests(unittest.TestCase):
    """Verify ULI hooks are correctly registered in hooks/hooks.json."""

    def setUp(self):
        self.hooks = json.loads(
            (ROOT / "hooks/hooks.json").read_text(encoding="utf-8")
        )

    def _commands_for_event(self, event: str) -> list:
        cmds = []
        for entry in self.hooks.get("hooks", {}).get(event, []):
            for hook in entry.get("hooks", []):
                cmds.append(hook.get("command", ""))
        return cmds

    def test_uli_detector_registered_in_user_prompt_submit(self):
        cmds = self._commands_for_event("UserPromptSubmit")
        self.assertTrue(
            any("uli-detector" in c for c in cmds),
            f"uli-detector.py not in UserPromptSubmit. Found: {cmds}"
        )

    def test_uli_stop_hook_registered_in_stop(self):
        cmds = self._commands_for_event("Stop")
        self.assertTrue(
            any("uli-stop-hook" in c for c in cmds),
            f"uli-stop-hook.sh not in Stop hooks. Found: {cmds}"
        )

    def test_both_ulw_and_uli_detectors_registered(self):
        cmds = self._commands_for_event("UserPromptSubmit")
        self.assertTrue(any("ulw-detector" in c for c in cmds), "ulw-detector must still be registered")
        self.assertTrue(any("uli-detector" in c for c in cmds), "uli-detector must be registered")

    def test_both_ulw_and_uli_stop_hooks_registered(self):
        cmds = self._commands_for_event("Stop")
        self.assertTrue(any("ulw-stop-hook" in c for c in cmds), "ulw-stop-hook must still be registered")
        self.assertTrue(any("uli-stop-hook" in c for c in cmds), "uli-stop-hook must be registered")


# ---------------------------------------------------------------------------
# ultrawork SKILL.md — ULI branch completeness
# ---------------------------------------------------------------------------

class UliSkillBranchTests(unittest.TestCase):
    """Verify ultrawork SKILL.md and ULI.md contain a complete ULI branch."""

    def setUp(self):
        self.skill_content = (ROOT / "skills" / "ultrawork" / "SKILL.md").read_text(encoding="utf-8")
        self.uli_content = (ROOT / "skills" / "ultrawork" / "ULI.md").read_text(encoding="utf-8")
        self.content = self.skill_content + "\n" + self.uli_content

    def test_uli_branch_header_present(self):
        self.assertIn("ULI — Ultra Loop Iteration Branch", self.content)

    def test_uli_done_tag_defined(self):
        self.assertIn("<uli-done>", self.content)

    def test_uli_state_file_referenced(self):
        self.assertIn("uli-state.json", self.content)

    def test_hard_acceptance_gate_defined(self):
        self.assertIn("Hard Acceptance Gate", self.content)

    def test_product_analysis_proposal_flow_described(self):
        self.assertIn("uli/<slug>/proposal.md", self.content)
        self.assertIn("research", self.content)

    def test_max_iterations_default_documented(self):
        import re
        self.assertRegex(
            self.content, r"max_iterations.*10\b|10\b.*max_iterations",
            "Default max_iterations=10 must appear in ULI branch"
        )

    def test_reject_retry_limit_documented(self):
        self.assertRegex(
            self.content,
            r"(?i)(REJECT.*max\s*2|max\s*2.*retry|retry.*2\s*loop|2.*retry|2.*loop)",
            "Reject retry limit (max 2) must be documented"
        )

    def test_uli_golden_rules_present(self):
        self.assertIn("ULI Golden Rules", self.content)

    def test_uli_state_transitions_documented(self):
        for phase in ["pd_generating", "dev_pipeline", "acceptance"]:
            with self.subTest(phase=phase):
                self.assertIn(phase, self.content,
                              f"Phase '{phase}' must appear in ULI branch")

    def test_product_state_md_referenced(self):
        self.assertIn("product-state.md", self.content)

    def test_uli_and_ulw_coexist(self):
        self.assertIn("<ulw-done>", self.skill_content, "ULW branch must be in SKILL.md")
        self.assertIn("<uli-done>", self.uli_content, "ULI branch must be in ULI.md")


# ---------------------------------------------------------------------------
# commands/uli.md content tests
# ---------------------------------------------------------------------------

class UliCommandDocTests(unittest.TestCase):
    """Verify commands/uli.md exists and documents the ULI command correctly."""

    def setUp(self):
        import re
        self.path = ROOT / "commands" / "uli.md"
        self.assertTrue(self.path.exists(), "commands/uli.md must exist")
        self.content = self.path.read_text(encoding="utf-8")
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", self.content, re.S)
        self.assertIsNotNone(match, "uli.md must have YAML frontmatter")

    def test_activation_examples_present(self):
        self.assertRegex(self.content, r"(?i)(uli\s+\w|/uli)", "Must show activation examples")

    def test_distinguishes_from_ulw(self):
        self.assertIn("ulw", self.content.lower(), "Must compare ULI to ULW")

    def test_documents_hard_acceptance(self):
        self.assertRegex(
            self.content,
            r"(?i)(hard.*accept|accept.*hard|build.*test|test.*build)",
            "Must document hard acceptance requirement"
        )

    def test_documents_pd_agent(self):
        self.assertRegex(
            self.content,
            r"(?i)(PD|product.*manager|product.*agent)",
            "Must mention PD agent"
        )

    def test_documents_max_iterations(self):
        self.assertRegex(
            self.content,
            r"(?i)(10|max.*iter|iter.*max)",
            "Must document iteration limit"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
