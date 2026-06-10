"""Tests for workflow script contract constants and helpers.

Validates that the canonical constants, enums, threshold tables, and
validation functions defined in the workflow scripts match the spec.
"""

import json
import re
import subprocess
import tempfile
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

    def test_diff_anchor_helper_inventory(self):
        """Contract: diff anchor resolution is helper-only with prompt fallback metadata."""
        assert "function resolveDiffAnchors(args, task, impl, stage)" in self.script
        for text in [
            "explicit_args_base_sha", "task_captured_base_sha", "merge_base_ref",
            "prompt_only_impl_base_sha", "unverified", "anchor_error",
            "no_repo", "invalid_sha", "missing_base_ref", "detached_head",
            "unborn_or_no_commits", "shallow_or_missing_base", "merge_conflict",
            "enforcement_mode: ENFORCEMENT_MODE",
        ]:
            assert text in self.script

    def test_diff_anchor_precedence_order(self):
        """Contract: explicit args > task base > merge-base > prompt-only impl > unverified."""
        ordered = [
            "args && args.base_sha",
            "task && (task.base_sha || task.captured_base_sha || task.git_base_sha)",
            "const baseRef = (args && args.base_ref) || defaultRef || 'main'",
            "source: 'merge_base_ref'",
            "impl && impl.base_sha",
            "source: 'unverified'",
        ]
        positions = [self.script.index(text) for text in ordered]
        assert positions == sorted(positions)

    def test_diff_anchor_resolution_precedence(self):
        result = self._eval_evidence_helper(r'''
            [
              resolveDiffAnchors({ base_sha: '1111111' }, { base_sha: '2222222' }, { base_sha: '3333333' }, 'spec_review'),
              resolveDiffAnchors({}, { captured_base_sha: '2222222' }, { base_sha: '3333333' }, 'spec_review'),
              resolveDiffAnchors({ git: { no_repo: true } }, {}, { base_sha: '3333333' }, 'spec_review'),
              resolveDiffAnchors({ base_ref: 'develop' }, {}, {}, 'spec_review')
            ]
        ''')
        assert result[0]["source"] == "explicit_args_base_sha"
        assert result[0]["base_sha"] == "1111111"
        assert result[1]["source"] == "task_captured_base_sha"
        assert result[1]["base_sha"] == "2222222"
        assert result[2]["source"] == "prompt_only_impl_base_sha"
        assert result[2]["base_sha"] == "3333333"
        assert result[2]["anchor_error"]["code"] == "prompt_only_merge_base_unverified"
        assert result[2]["enforcement_mode"] == "prompt_only"
        assert result[3]["source"] == "merge_base_ref"
        assert result[3]["base_ref"] == "develop"
        assert result[3]["enforcement_mode"] == "prompt_only"

    def test_diff_anchor_resolution_uses_default_branch_metadata(self):
        result = self._eval_evidence_helper(r'''
            [
              resolveDiffAnchors({ default_branch: 'trunk' }, {}, {}, 'spec_review'),
              resolveDiffAnchors({ git: { default_branch: 'develop', missing_base_ref: 'main unavailable' } }, {}, {}, 'code_review')
            ]
        ''')
        assert result[0]["base_ref"] == "trunk"
        assert result[0]["base_ref_source"] == "default_branch_ref"
        assert result[1]["base_ref"] == "develop"
        assert result[1]["base_ref_source"] == "default_branch_ref"
        assert result[1]["anchor_error"]["code"] == "missing_base_ref"

    def test_diff_anchor_prompt_is_appended_to_review_and_fix_prompts(self):
        result = self._eval_evidence_helper(r'''
            [
              specReviewPrompt({ id: 'task-1', description: 'Do x' }, { summary: 'Done', files_modified: ['a.js'] }).includes('## Diff Anchor Metadata'),
              codeReviewPrompt({ summary: 'Done', files_modified: ['a.js'] }, 'task-1', { id: 'task-1' }).includes('## Diff Anchor Metadata'),
              fixPrompt([], ['a.js'], { id: 'task-1' }, { files_modified: ['a.js'] }, 'spec_fix').includes('## Diff Anchor Metadata')
            ]
        ''')
        assert result == [True, True, True]

    def test_diff_anchor_resolution_error_fallback_metadata(self):
        result = self._eval_evidence_helper(r'''
            [
              resolveDiffAnchors({ base_sha: 'not-a-sha' }, {}, {}, 'code_review'),
              resolveDiffAnchors({ git: { no_repo: true } }, {}, { base_sha: '3333333' }, 'code_review'),
              resolveDiffAnchors({ git: { missing_base_ref: 'origin/main unavailable' } }, {}, {}, 'code_review')
            ]
        ''')
        assert result[0]["anchor_error"]["code"] == "invalid_sha"
        assert result[1]["source"] == "prompt_only_impl_base_sha"
        assert result[1]["base_sha"] == "3333333"
        assert result[1]["anchor_error"]["code"] == "no_repo"
        assert result[2]["source"] == "unverified"
        assert result[2]["anchor_error"] == {"code": "missing_base_ref", "detail": "origin/main unavailable"}

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

    def _eval_evidence_helper(self, expression):
        helper_prefix = self.script.split("// ── Result adapter", 1)[0]
        helper_prefix = re.sub(r"export const meta", "const meta", helper_prefix)
        node_script = helper_prefix + "\nconsole.log(JSON.stringify(" + expression + "))"
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
            f.write(node_script)
            node_path = f.name
        try:
            result = subprocess.run(
                ["node", node_path],
                check=True,
                capture_output=True,
                text=True,
            )
        finally:
            Path(node_path).unlink(missing_ok=True)
        return json.loads(result.stdout)

    def test_extract_evidence_normalizes_sources_and_requirement(self):
        result = self._eval_evidence_helper(r'''
            extractEvidence(
              { id: 'task-2', tests: ['pytest planned'], verification: ['manual planned'], runtime_evidence_required: 'required' },
              { status: 'DONE', verification_results: [{ command: 'agent cmd', exit_code: 0 }], commit_sha: 'abc123', files_modified: ['a.js'] },
              { command_results: [{ command: 'pytest', exit_code: 0, output: 'ok' }], evidence_paths: ['C:/tmp/e.png'] }
            )
        ''')
        assert result["runtime_evidence_required"] == "artifact"
        assert result["planned_verification"] == ["pytest planned", "manual planned"]
        assert result["executed_commands"][0]["command"] == "pytest"
        assert result["evidence_paths"] == ["C:/tmp/e.png"]
        assert result["commit_sha"] == "abc123"

    def test_extract_evidence_legacy_runtime_requirement_defaults(self):
        result = self._eval_evidence_helper(r'''
            [
              extractEvidence({}, {}, {}).runtime_evidence_required,
              extractEvidence({ runtime_evidence_required: true }, {}, {}).runtime_evidence_required,
              extractEvidence({ runtime_evidence_required: false }, {}, {}).runtime_evidence_required,
              extractEvidence({ runtime_evidence_required: 'unknown' }, {}, {}).runtime_evidence_required
            ]
        ''')
        assert result == ["none", "command", "none", "none"]

    def test_validate_implementation_evidence_blocks_missing_required_command(self):
        result = self._eval_evidence_helper(r'''
            validateImplementationEvidence(
              { required_commands: ['pytest'], runtime_evidence_required: true },
              { status: 'DONE', verification_results: [] },
              {},
              null
            )
        ''')
        assert result["passed"] is False
        assert result["status"] == "blocked"
        assert "missing_required_command: pytest" in result["reasons"]

    def test_validate_implementation_evidence_accepts_substitute_nonzero_concerns_and_alias(self):
        result = self._eval_evidence_helper(r'''
            validateImplementationEvidence(
              { required_commands: ['pytest'], command_substitutes: { pytest: ['uv run pytest'] }, expected_nonzero_commands: ['lint'], runtime_evidence_required: true, acceptance_refs: ['REQ-1'] },
              { status: 'DONE_WITH_CONCERNS', concerns: ['REQ-1 deferred w/ user ok'], dirty_commit_sha: 'dirty-ok' },
              { command_results: [
                { command: 'uv run pytest tests', exit_code: 0 },
                { command: 'lint', exit_code: 1 }
              ] },
              { acceptance_refs: ['REQ-1'] }
            )
        ''')
        assert result["passed"] is True
        assert result["status"] == "passed"
        assert result["evidence"]["commit_sha"] == "dirty-ok"

    def test_validate_implementation_evidence_accepts_required_expected_nonzero_command(self):
        result = self._eval_evidence_helper(r'''
            validateImplementationEvidence(
              { required_commands: ['lint'], expected_nonzero_commands: ['lint'], runtime_evidence_required: true },
              { status: 'DONE' },
              { command_results: [{ command: 'lint', exit_code: 1 }] },
              null
            )
        ''')
        assert result["passed"] is True
        assert result["status"] == "passed"

    def test_validate_implementation_evidence_blocks_unexpected_nonzero_and_paths(self):
        result = self._eval_evidence_helper(r'''
            validateImplementationEvidence(
              { runtime_evidence_required: 'artifact' },
              { status: 'DONE', evidence_paths: ['Z:/definitely/missing/evidence.txt'] },
              { command_results: [{ command: 'pytest', exit_code: 1 }], path_exists: { 'Z:/definitely/missing/evidence.txt': false } },
              null
            )
        ''')
        assert result["passed"] is False
        assert "command_failed: pytest" in result["reasons"]
        assert "evidence_path_missing: Z:/definitely/missing/evidence.txt" in result["reasons"]

    def test_extract_evidence_uses_agent_results_only_when_controller_prompt_only(self):
        result = self._eval_evidence_helper(r'''
            [
              extractEvidence(
                { required_commands: ['pytest'] },
                { verification_results: [{ command: 'agent pytest', exit_code: 0 }] },
                { command_results: [{ command: 'controller pytest', exit_code: 0 }] }
              ).executed_commands[0].command,
              extractEvidence(
                { required_commands: ['pytest'] },
                { verification_results: [{ command: 'agent pytest', exit_code: 0 }] },
                { prompt_only: true }
              ).executed_commands[0].command
            ]
        ''')
        assert result == ["controller pytest", "agent pytest"]

    def test_validate_implementation_evidence_blocks_status_and_runtime_command(self):
        result = self._eval_evidence_helper(r'''
            [
              validateImplementationEvidence({}, { status: 'BLOCKED', blocker_detail: 'missing token' }, {}, null),
              validateImplementationEvidence({ runtime_evidence_required: true }, { status: 'DONE' }, { prompt_only: true }, null),
              validateImplementationEvidence({}, { status: 'DONE_WITH_CONCERNS', concerns: [] }, {}, null)
            ]
        ''')
        assert "implementation_blocked: missing token" in result[0]["reasons"]
        assert "missing_runtime_command_evidence" in result[1]["reasons"]
        assert "missing_concerns" in result[2]["reasons"]


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
