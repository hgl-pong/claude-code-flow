"""Tests for workflow script contract constants and helpers.

Validates that the canonical constants, enums, threshold tables, and
validation functions defined in the workflow scripts match the spec.
"""

import json
import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills" / "auto-mode" / "workflows"
FULL_AUTO = SKILLS_DIR / "full-auto-pipeline.workflow.js"
EXECUTE_PLAN = SKILLS_DIR / "execute-plan.workflow.js"

CANONICAL_GATES = [
    "tasks_executed",
    "reviews_passed",
    "tests_pass",
    "runtime_evidence",
    "spec_verified",
    "final_review",
    "git_clean",
]

PHASE_ORDER = [
    "scope", "research", "synthesize_spec", "review_spec",
    "write_plan", "review_plan", "parse_plan", "execute", "gates", "finalize",
]

RESULT_PARTITIONS = ["passed", "completed", "blocked", "stalled", "failed_review", "needs_escalation"]

BLOCKER_TAXONOMY = [
    "agent_output_invalid", "merge_conflict", "permissions", "external_service",
    "tooling_unavailable", "test_failure", "runtime_failure", "dependency_failure",
    "architecture_decision", "scope_too_large", "missing_context",
]

ESCALATION_LADDER = [
    "schema_retry", "self_service_retry", "stronger_model",
    "split_subtask", "enriched_context", "ask_user",
]

REVIEW_SEVERITIES = ["Critical", "High", "Important", "Minor", "Info"]

TASK_RISKS = ["low", "medium", "high", "critical"]

TERMINAL_STATUSES = ["DONE", "STOPPED_ASK_USER", "FAILED_FATAL", "CANCELLED"]
NONTERMINAL_STATUSES = ["ACTIVE", "PAUSED_COMPACTING", "BLOCKED_ESCALATING"]


def _read_script(path: Path) -> str:
    assert path.exists(), f"Script not found: {path}"
    return path.read_text(encoding="utf-8")


def _assert_const_in(script: str, const_name: str, expected_values: list) -> None:
    """Check that a const array in the script contains exactly the expected values."""
    # Match: const NAME = ['a', 'b', ...]
    pattern = rf"const\s+{const_name}\s*=\s*\[([^\]]+)\]"
    m = re.search(pattern, script)
    assert m, f"const {const_name} not found in script"
    # Extract string literals
    found = re.findall(r"'([^']+)'", m.group(1)) + re.findall(r'"([^"]+)"', m.group(1))
    assert found == expected_values, (
        f"{const_name}: expected {expected_values}, got {found}"
    )


# ── full-auto-pipeline.workflow.js contract tests ──────────────────────


class TestFullAutoConstants:
    """Contract: full-auto-pipeline.workflow.js defines canonical constants."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(FULL_AUTO)

    def test_phase_order(self):
        _assert_const_in(self.script, "PHASE_ORDER", PHASE_ORDER)

    def test_canonical_gates(self):
        _assert_const_in(self.script, "CANONICAL_GATES", CANONICAL_GATES)

    def test_result_partitions(self):
        _assert_const_in(self.script, "RESULT_PARTITIONS", RESULT_PARTITIONS)

    def test_blocker_taxonomy(self):
        _assert_const_in(self.script, "BLOCKER_TAXONOMY", BLOCKER_TAXONOMY)

    def test_escalation_ladder(self):
        _assert_const_in(self.script, "ESCALATION_LADDER", ESCALATION_LADDER)

    def test_review_severities(self):
        _assert_const_in(self.script, "REVIEW_SEVERITIES", REVIEW_SEVERITIES)

    def test_task_risks(self):
        _assert_const_in(self.script, "TASK_RISKS", TASK_RISKS)

    def test_terminal_statuses(self):
        _assert_const_in(self.script, "TERMINAL_STATUSES", TERMINAL_STATUSES)

    def test_nonterminal_statuses(self):
        _assert_const_in(self.script, "NONTERMINAL_STATUSES", NONTERMINAL_STATUSES)

    def test_gate_count_is_seven(self):
        assert len(CANONICAL_GATES) == 7

    def test_no_external_imports(self):
        assert "require(" not in self.script
        assert "import " not in self.script or "export const meta" in self.script

    def test_review_threshold_table_exists(self):
        assert "REVIEW_THRESHOLD" in self.script
        assert "spec_review" in self.script
        assert "code_review" in self.script
        assert "final_review" in self.script

    def test_is_issue_blocking_function(self):
        assert "function isIssueBlocking" in self.script

    def test_validate_gate_set_function(self):
        assert "function validateGateSet" in self.script


# ── execute-plan.workflow.js contract tests ────────────────────────────


class TestExecutePlanConstants:
    """Contract: execute-plan.workflow.js defines shared constants."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(EXECUTE_PLAN)

    def test_result_partitions(self):
        _assert_const_in(self.script, "RESULT_PARTITIONS", RESULT_PARTITIONS)

    def test_blocker_taxonomy(self):
        _assert_const_in(self.script, "BLOCKER_TAXONOMY", BLOCKER_TAXONOMY)

    def test_escalation_ladder(self):
        _assert_const_in(self.script, "ESCALATION_LADDER", ESCALATION_LADDER)

    def test_review_severities(self):
        _assert_const_in(self.script, "REVIEW_SEVERITIES", REVIEW_SEVERITIES)

    def test_task_risks(self):
        _assert_const_in(self.script, "TASK_RISKS", TASK_RISKS)

    def test_is_issue_blocking_function(self):
        assert "function isIssueBlocking" in self.script

    def test_no_external_imports(self):
        assert "require(" not in self.script

    def test_prompt_builder_inventory(self):
        """Contract: execute-plan exposes all prompt builders used by loops."""
        for name in [
            "implementPrompt", "specReviewPrompt", "codeReviewPrompt",
            "fixPrompt", "selfServicePrompt",
        ]:
            assert f"function {name}" in self.script

    def test_runtime_primitive_inventory(self):
        """Contract: controller runtime lacks command primitive; enforcement is prompt-only."""
        assert "const COMMAND_EXECUTION_PRIMITIVE" in self.script
        assert "workflow_agent_only" in self.script
        assert "const ENFORCEMENT_MODE = 'prompt_only'" in self.script

    def test_state_resume_inventory(self):
        """Contract: resume/state patch paths remain discoverable."""
        for text in [
            "result_replay", "state_patch", "partitions", "final_review_run",
            "passed", "completed", "blocked", "stalled", "failed_review", "needs_escalation",
        ]:
            assert text in self.script

    def test_review_loop_inventory(self):
        """Contract: review/fix/re-review loops remain present."""
        for text in [
            "MAX_RETRIES", "fix-spec", "spec-review:", "fix-code", "code-review:",
            "hasBlockingIssues", "_spec_review_exhausted", "_code_review_exhausted",
        ]:
            assert text in self.script

    def test_final_review_gate6_inventory(self):
        """Contract: final review is guarded for Gate 6 consumption."""
        for text in [
            "Final Review only when ALL tasks passed", "partitions.completed.length === totalTasks",
            "allOtherPartitionsEmpty", "final_review: finalReview", "opts('final-review'",
        ]:
            assert text in self.script


# ── Cross-script consistency ──────────────────────────────────────────


class TestCrossScriptConsistency:
    """Contract: both scripts agree on shared constants."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.full = _read_script(FULL_AUTO)
        self.exec = _read_script(EXECUTE_PLAN)

    def _extract_const(self, script: str, name: str) -> list:
        pattern = rf"const\s+{name}\s*=\s*\[([^\]]+)\]"
        m = re.search(pattern, script)
        if not m:
            return []
        return re.findall(r"'([^']+)'", m.group(1)) + re.findall(r'"([^"]+)"', m.group(1))

    def test_partitions_match(self):
        assert self._extract_const(self.full, "RESULT_PARTITIONS") == \
               self._extract_const(self.exec, "RESULT_PARTITIONS")

    def test_blocker_taxonomy_matches(self):
        assert self._extract_const(self.full, "BLOCKER_TAXONOMY") == \
               self._extract_const(self.exec, "BLOCKER_TAXONOMY")

    def test_escalation_ladder_matches(self):
        assert self._extract_const(self.full, "ESCALATION_LADDER") == \
               self._extract_const(self.exec, "ESCALATION_LADDER")

    def test_severities_match(self):
        assert self._extract_const(self.full, "REVIEW_SEVERITIES") == \
               self._extract_const(self.exec, "REVIEW_SEVERITIES")

    def test_risks_match(self):
        assert self._extract_const(self.full, "TASK_RISKS") == \
               self._extract_const(self.exec, "TASK_RISKS")

    def test_completed_backward_compat_alias(self):
        """completed[] must equal passed[] for v1."""
        partitions = self._extract_const(self.full, "RESULT_PARTITIONS")
        assert "completed" in partitions
        assert "passed" in partitions

    def test_result_partition_invariants(self):
        """Each task appears in exactly one partition; completed == passed."""
        partitions = self._extract_const(self.exec, "RESULT_PARTITIONS")
        assert len(partitions) == len(set(partitions)), "Partitions must be unique"


# ── Gate order enforcement ────────────────────────────────────────────


class TestGateOrder:
    """Contract: gates are exactly 7 canonical gates in fixed order."""

    def test_gate_count(self):
        assert len(CANONICAL_GATES) == 7

    def test_gate_order(self):
        assert CANONICAL_GATES == [
            "tasks_executed",
            "reviews_passed",
            "tests_pass",
            "runtime_evidence",
            "spec_verified",
            "final_review",
            "git_clean",
        ]

    def test_gate_4_is_runtime_evidence(self):
        assert CANONICAL_GATES[3] == "runtime_evidence"
