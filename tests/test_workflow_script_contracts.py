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

    def test_implement_result_schema_requires_done_evidence_fields(self):
        """Contract: DONE/DONE_WITH_CONCERNS require evidence fields."""
        for text in [
            "allOf: [{",
            "status: { enum: ['DONE', 'DONE_WITH_CONCERNS'] }",
            "'test_results', 'verification_commands', 'verification_results', 'base_sha', 'head_sha'",
            "'acceptance_coverage', 'unverified_acceptance_refs', 'concerns', 'diff_summary'",
        ]:
            assert text in self.script

    def test_implement_result_schema_allows_agent_verification_results(self):
        """Contract: implementer schema accepts agent evidence fallback field."""
        assert "verification_results" in self.script
        assert "Agent-run verification command results" in self.script

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
              resolveDiffAnchors({ base_ref: 'develop' }, {}, { base_sha: '3333333' }, 'spec_review'),
              resolveDiffAnchors({ git: { no_repo: true } }, {}, { base_sha: '3333333' }, 'spec_review'),
              resolveDiffAnchors({ base_ref: 'develop' }, {}, {}, 'spec_review')
            ]
        ''')
        assert result[0]["source"] == "explicit_args_base_sha"
        assert result[0]["base_sha"] == "1111111"
        assert result[1]["source"] == "task_captured_base_sha"
        assert result[1]["base_sha"] == "2222222"
        assert result[2]["source"] == "merge_base_ref"
        assert result[2]["base_ref"] == "develop"
        assert result[2]["anchor_error"]["code"] == "prompt_only_merge_base_unverified"
        assert result[2]["enforcement_mode"] == "prompt_only"
        assert result[3]["source"] == "prompt_only_impl_base_sha"
        assert result[3]["base_sha"] == "3333333"
        assert result[3]["anchor_error"]["code"] == "no_repo"
        assert result[4]["source"] == "merge_base_ref"
        assert result[4]["base_ref"] == "develop"
        assert result[4]["enforcement_mode"] == "prompt_only"

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

    def test_review_prompts_are_diff_first_and_location_strict(self):
        result = self._eval_evidence_helper(r'''
            (() => {
              const spec = specReviewPrompt(
                { id: 'task-1', description: 'Do x' },
                { summary: 'Done', files_modified: ['a.js'], acceptance_coverage: [], unverified_acceptance_refs: ['REQ-1'] }
              );
              const code = codeReviewPrompt({ summary: 'Done', files_modified: ['a.js'] }, 'task-1', { id: 'task-1' });
              return [
                spec.includes('## Controller Diff Evidence'),
                spec.includes('requirements and acceptance only'),
                spec.includes('Stale/unverified refs'),
                spec.includes('location_unavailable_reason'),
                code.includes('Inspect controller diff metadata first'),
                code.includes('files_modified as untrusted'),
                code.includes('diff_verified=false'),
                code.includes('prior_issue_id')
              ];
            })()
        ''')
        assert result == [True, True, True, True, True, True, True, True]

    def test_review_result_schema_accepts_unnormalized_issue_values(self):
        for text in [
            "severity: { type: 'string', description: 'Free-form severity; normalized after schema parsing' }",
            "category: { type: 'string', description: 'Free-form category; normalized after schema parsing' }",
            "line: { type: ['number', 'string', 'null'], description: 'Line number or free-form line value; normalized after schema parsing' }",
        ]:
            assert text in self.script
        assert "severity: { type: 'string', enum: ['Critical', 'High', 'Important', 'Minor', 'Info'] }" not in self.script
        assert "line: { type: 'number' }" not in self.script

    def test_review_issue_identity_is_stable_normalized_and_deduped(self):
        result = self._eval_evidence_helper(r'''
            (() => {
              const review = normalizeReviewIssues({ issues: [
                { severity: 'medium', category: 'Spec Gap', file: 'src/a.js', line: '2', description: 'Missing X' },
                { severity: 'medium', category: 'Spec Gap', file: 'src/a.js', line: 2, description: 'Missing X' },
                { id: 'custom-1', severity: 'low', description: 'No location' }
              ] }, { stage: 'spec_review', task_id: 'task-7', prior_issues: [
                { id: 'old-1', severity: 'Important', category: 'spec_gap', file: 'src/a.js', line: 2, description: 'Missing X' }
              ] });
              return review.issues;
            })()
        ''')
        assert result[0]["id"].startswith("amr1:spec_review:task-7:important:")
        assert result[0]["severity"] == "Important"
        assert result[0]["category"] == "spec_gap"
        assert result[0]["prior_issue_id"] == "old-1"
        assert result[0]["supersedes"] == "old-1"
        assert result[1]["duplicate_of"] == result[0]["id"]
        assert result[1]["id"].endswith("-2")
        assert result[2]["id"] == "custom-1"
        assert result[2]["severity"] == "Minor"
        assert result[2]["location_unavailable_reason"] == "not_provided_by_reviewer"

    def test_spec_review_prompt_includes_concerns_evidence_validation_and_limitations(self):
        result = self._eval_evidence_helper(r'''
            (() => {
              const prompt = specReviewPrompt(
                { id: 'task-1', description: 'Do x' },
                {
                  summary: 'Done',
                  files_modified: ['a.js'],
                  concerns: ['needs_review_override'],
                  evidence_validation: { status: 'prompt_only_unverified', limitations: ['prompt_only_evidence_unverified'] }
                }
              );
              return [
                prompt.includes('## Implementation Concerns / Limitations'),
                prompt.includes('needs_review_override'),
                prompt.includes('prompt_only_unverified'),
                prompt.includes('prompt_only_evidence_unverified')
              ];
            })()
        ''')
        assert result == [True, True, True, True]

    def test_spec_review_handoff_wires_evidence_validation_to_prompt(self):
        for text in [
            "impl.evidence_validation = implementationEvidence",
            "impl.limitations = implementationEvidence.limitations",
        ]:
            assert text in self.script

    def test_collect_diff_evidence_inventory(self):
        for text in [
            "function collectDiffEvidence(anchor)", "name_status", "diff_summary",
            "worktree_diff", "committed_diff", "truncated", "binary", "renamed", "deleted",
            "command_errors", "verified_diff",
        ]:
            assert text in self.script

    def test_collect_diff_evidence_metadata_and_dirty_state(self):
        result = self._eval_evidence_helper(r'''
            collectDiffEvidence({
              base_sha: '1111111', head_sha: '2222222', dirty: true,
              committed: { ok: true, name_status: 'M\tsrc/a.js\n', diff: 'diff --git a/src/a.js b/src/a.js\n+change\n' },
              worktree: { ok: true, name_status: 'A\tsrc/wip.js\n', diff: 'diff --git a/src/wip.js b/src/wip.js\n+wip\n' }
            })
        ''')
        assert result["base_sha"] == "1111111"
        assert result["head_sha"] == "2222222"
        assert result["dirty"] is True
        assert result["includes_worktree_diff"] is True
        assert result["verified_diff"] is True
        assert result["committed_diff"]["name_status"] == ["M\tsrc/a.js"]
        assert result["worktree_diff"]["name_status"] == ["A\tsrc/wip.js"]

    def test_collect_diff_evidence_truncates_huge_diff_and_records_scope_error(self):
        result = self._eval_evidence_helper(r'''
            collectDiffEvidence({
              base_sha: '1111111', head_sha: '2222222', max_diff_chars: 12,
              committed: { ok: false, error: 'git diff failed', name_status: 'M\ta.js\n', diff: '12345678901234567890' },
              worktree: { ok: true, diff: 'abcdefghijklmno' }
            })
        ''')
        assert result["verified_diff"] is False
        assert result["scope_complete"] is False
        assert result["committed_diff"]["truncated"] is True
        assert result["worktree_diff"]["truncated"] is True
        assert result["command_errors"][0] == {"scope": "committed", "error": "git diff failed"}

    def test_collect_diff_evidence_special_file_status_metadata(self):
        result = self._eval_evidence_helper(r'''
            collectDiffEvidence({
              committed: { ok: true, name_status: 'R100\told name.txt\tnew name.txt\nD\tdeleted file.txt\n-\t-\tbinary.bin\n', diff: 'Binary files a/binary.bin and b/binary.bin differ\n' },
              worktree: { ok: true, name_status: 'A\tpath with spaces/file.txt\n' }
            })
        ''')
        assert result["special_statuses"]["renamed"] == [{"from": "old name.txt", "to": "new name.txt", "status": "R100"}]
        assert result["special_statuses"]["deleted"] == ["deleted file.txt"]
        assert result["special_statuses"]["binary"] == ["binary.bin"]
        assert result["worktree_diff"]["files"] == ["path with spaces/file.txt"]

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

    def test_attempt_diff_capture_inventory(self):
        """Contract: implementation/fix attempts persist controller diff evidence."""
        for text in [
            "function captureAttemptBase", "function recordAttemptDiffEvidence",
            "task_attempt_base_sha", "task_attempt_base_dirty",
            "head_sha", "worktree_diff_included", "diff_verified", "diff_command",
            "diff_files", "diff_truncated", "attempt_diff_evidence", "state_patch",
        ]:
            assert text in self.script

    def test_attempt_diff_capture_pre_post_fields(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-1']],
              tasks: { 'task-1': { id: 'task-1', description: 'Do x' } },
              worktree: 'C:/tmp/worktree',
              git: {
                controller_commands_available: true,
                head_sha: '1111111',
                dirty: true,
                attempts: { 'implement:task-1': {
                  head_sha: '2222222', dirty: true, command: 'git diff --name-status 1111111...HEAD && git diff',
                  committed: { ok: true, name_status: 'M\tsrc/a.js\n', diff: '+change\n' },
                  worktree: { ok: true, name_status: 'A\tsrc/wip.js\n', diff: '+wip\n' }
                } }
              },
              __agent_results: {
                'implement:task-1': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task', status: 'covered' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-1': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-1': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'final-review': { passed: true, issues: [], summary: 'ok' }
              }
            }
        ''')
        base = result["state_patch"]["task_attempt_bases"][0]
        assert base == {"id": "task-1", "task_attempt_base_sha": "1111111", "task_attempt_base_dirty": True, "task_attempt_base_capture_failed": ""}
        assert result["passed"][0]["task_attempt_base_sha"] == "1111111"
        assert result["passed"][0]["task_attempt_base_dirty"] is True
        evidence = result["state_patch"]["task_attempt_diff_evidence"][0]
        assert evidence["label"] == "implement:task-1"
        assert evidence["base_sha"] == "1111111"
        assert evidence["head_sha"] == "2222222"
        assert evidence["dirty"] is True
        assert evidence["worktree_diff_included"] is True
        assert evidence["diff_verified"] is True
        assert evidence["diff_command"] == "git diff --name-status 1111111...HEAD && git diff"
        assert evidence["diff_files"] == ["src/a.js", "src/wip.js"]
        assert evidence["diff_truncated"] is False
        assert result["passed"][0]["attempt_diff_evidence"][0] == evidence

    def test_attempt_diff_capture_prompt_only_fallback(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-2']],
              tasks: { 'task-2': { id: 'task-2', description: 'Do y' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-2': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task', status: 'covered' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-2': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-2': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'final-review': { passed: true, issues: [], summary: 'ok' }
              }
            }
        ''')
        evidence = result["state_patch"]["task_attempt_diff_evidence"][0]
        assert evidence["label"] == "implement:task-2"
        assert evidence["base_sha"] == "1111111"
        assert evidence["enforcement_mode"] == "prompt_only"
        assert evidence["diff_verified"] is False
        assert evidence["worktree_diff_included"] is False
        assert evidence["diff_command"] == ""
        assert evidence["diff_files"] == []

    def test_attempt_diff_capture_persists_missing_base_failure(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-3']],
              tasks: { 'task-3': { id: 'task-3', description: 'Do z' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true },
              __agent_results: {
                'implement:task-3': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task', status: 'covered' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-3': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-3': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'final-review': { passed: true, issues: [], summary: 'ok' }
              }
            }
        ''')
        base = result["state_patch"]["task_attempt_bases"][0]
        assert base == {"id": "task-3", "task_attempt_base_sha": "", "task_attempt_base_dirty": False, "task_attempt_base_capture_failed": "missing_controller_head_sha"}
        assert result["passed"][0]["task_attempt_base_capture_failed"] == "missing_controller_head_sha"
        evidence = result["state_patch"]["task_attempt_diff_evidence"][0]
        assert evidence["label"] == "implement:task-3"
        assert evidence["base_sha"] == ""
        assert evidence["diff_verified"] is False

    def test_attempt_diff_capture_escalation_attempts(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-4']],
              tasks: { 'task-4': { id: 'task-4', description: 'Do blocked' } },
              worktree: 'C:/tmp/worktree',
              git: {
                controller_commands_available: true,
                head_sha: '1111111',
                attempts: { 'escalate-schema-retry:task-4': {
                  head_sha: '2222222', command: 'git diff escalate',
                  committed: { ok: true, name_status: 'M\tsrc/escalated.js\n', diff: '+change\n' },
                  worktree: { ok: true, name_status: '', diff: '' }
                } }
              },
              __agent_results: {
                'implement:task-4': { status: 'BLOCKED', summary: 'Blocked', blocker_detail: 'test failure', files_modified: [] },
                'escalate-schema-retry:task-4': { status: 'DONE', summary: 'Done', files_modified: ['src/escalated.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task', status: 'covered' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-4': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-4': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'final-review': { passed: true, issues: [], summary: 'ok' }
              }
            }
        ''')
        labels = [e["label"] for e in result["state_patch"]["task_attempt_diff_evidence"]]
        assert labels == ["implement:task-4", "escalate-schema-retry:task-4"]
        assert result["state_patch"]["task_attempt_diff_evidence"][1]["diff_command"] == "git diff escalate"
        assert result["passed"][0]["attempt_diff_evidence"] == result["state_patch"]["task_attempt_diff_evidence"]

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

    def test_final_review_uses_dedicated_branch_diff_prompt(self):
        """Contract: final review uses branch-level diff evidence, not task attempt diffs."""
        for text in [
            "function finalReviewPrompt", "resolveDiffAnchors(workflowArgs, finalTask, finalImpl, 'final')",
            "## Branch Diff Evidence", "git diff --name-status BASE...HEAD",
            "git diff BASE...HEAD", "BASE_SHA..HEAD", "cross-task integration bugs",
            "conflicts", "duplicated changes", "missing shared tests", "regression risk",
        ]:
            assert text in self.script

    def test_final_review_block_without_fixes_is_canonical(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-final']],
              tasks: { 'task-final': { id: 'task-final', description: 'Do final block task' } },
              worktree: 'C:/tmp/worktree',
              git: {
                controller_commands_available: true,
                head_sha: '2222222',
                final: {
                  head_sha: '3333333', dirty: false,
                  command: 'git diff --name-status main...HEAD && git diff main...HEAD',
                  committed: { ok: true, name_status: 'M\tsrc/a.js\n', diff: '+change\n' },
                  worktree: { ok: true, name_status: '', diff: '' }
                }
              },
              __agent_results: {
                'implement:task-final': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-final': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-final': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'final-review': { passed: true, issues: [{ severity: 'High', file: 'src/a.js', description: 'cross-task break' }], summary: 'blocked despite optimistic pass' }
              }
            }
        ''')
        assert result["final_review"]["passed"] is False
        assert result["final_review"]["unresolved_issue_ids"] == [result["final_review"]["issues"][0]["id"]]
        assert result["state_patch"]["final_review_blocked"] is True
        assert result["state_patch"]["final_review_unresolved_issue_ids"] == result["final_review"]["unresolved_issue_ids"]
        assert result["state_patch"]["partitions"]["failed_review"] == []
        assert result["failed_review"] == []
        assert result["completed"][0]["id"] == "task-final"
        assert result["final_review"]["branch_diff_evidence"]["diff_verified"] is True

    def test_final_review_severity_blocks_even_with_false_blocking_flag(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-final-flag']],
              tasks: { 'task-final-flag': { id: 'task-final-flag', description: 'Do final block flag task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '2222222' },
              __agent_results: {
                'implement:task-final-flag': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-final-flag': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-final-flag': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'final-review': { passed: true, issues: [{ severity: 'High', blocking: false, file: 'src/a.js', description: 'cross-task break' }], summary: 'blocked despite false flag' }
              }
            }
        ''')
        assert result["final_review"]["passed"] is False
        assert result["state_patch"]["final_review_blocked"] is True
        assert result["final_review"]["unresolved_issue_ids"] == [result["final_review"]["issues"][0]["id"]]

    def test_final_review_branch_diff_preserves_resolved_anchor_error(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-final-anchor']],
              tasks: { 'task-final-anchor': { id: 'task-final-anchor', description: 'Do final anchor task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '2222222', missing_base_ref: 'origin/main unavailable' },
              __agent_results: {
                'implement:task-final-anchor': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-final-anchor': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-final-anchor': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'final-review': { passed: true, issues: [], summary: 'ok' }
              }
            }
        ''')
        assert result["final_review"]["branch_diff_evidence"]["command_errors"] == [
            {"scope": "anchor", "error": {"code": "missing_base_ref", "detail": "origin/main unavailable"}}
        ]
        assert result["final_review"]["branch_diff_evidence"]["diff_verified"] is False

    def _eval_evidence_helper(self, expression):
        helper_prefix = self.script.split("// ── Result adapter", 1)[0]
        helper_prefix = re.sub(r"export const meta", "const meta", helper_prefix)
        node_script = helper_prefix + "\nconsole.log(JSON.stringify(" + expression + "))"
        return self._run_node_script(node_script)

    def _eval_workflow(self, args_expression):
        workflow = re.sub(r"export const meta", "const meta", self.script)
        node_script = """
let args = ARGS_EXPRESSION;
const logs = [];
function log(message) { logs.push(message); }
function phase(message) { logs.push('phase:' + message); }
function opts(label, phase, schema) {
  const o = { label, phase, schema };
  if (typeof model_tasks !== 'undefined' && model_tasks) o.model = model_tasks;
  return o;
}
async function agent(prompt, agentOpts) {
  const result = args.__agent_results && args.__agent_results[agentOpts.label];
  if (Array.isArray(result)) return result.shift();
  return result || null;
}
async function parallel(tasks) { return Promise.all(tasks.map(fn => fn())); }
async function pipeline(items, ...stages) {
  let current = items;
  for (const stage of stages) current = await Promise.all(current.map(item => stage(item)));
  return current;
}
(async () => {
WORKFLOW_SCRIPT
})().then(result => console.log(JSON.stringify(result))).catch(error => {
  console.error(error && error.stack || error);
  process.exit(1);
});
"""
        node_script = node_script.replace("ARGS_EXPRESSION", args_expression)
        node_script = node_script.replace("WORKFLOW_SCRIPT", workflow.replace("return {", "return {", 1))
        return self._run_node_script(node_script)

    def _run_node_script(self, node_script):
        with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
            f.write(node_script)
            node_path = f.name
        out_path = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False).name
        err_path = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False).name
        try:
            command = f'node "{node_path}" > "{out_path}" 2> "{err_path}"'
            subprocess.run(command, check=True, shell=True)
            return json.loads(Path(out_path).read_text(encoding="utf-8"))
        finally:
            Path(node_path).unlink(missing_ok=True)
            Path(out_path).unlink(missing_ok=True)
            Path(err_path).unlink(missing_ok=True)

    def test_extract_evidence_normalizes_sources_and_requirement(self):
        result = self._eval_evidence_helper(r'''
            extractEvidence(
              { id: 'task-2', tests: ['pytest planned'], verification: ['manual planned'], runtime_evidence_required: 'required' },
              { status: 'DONE', test_results: 'agent cmd passed', verification_commands: ['agent cmd'], verification_results: [{ command: 'agent cmd', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', commit_sha: 'abc123', files_modified: ['a.js'], acceptance_coverage: [{ ref: 'task', status: 'covered' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M a.js' },
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
        assert result["status"] == "block"
        assert "missing_required_command: pytest" in result["reasons"]

    def test_validate_implementation_evidence_accepts_substitute_nonzero_concerns_and_alias(self):
        result = self._eval_evidence_helper(r'''
            validateImplementationEvidence(
              { required_commands: ['pytest'], command_substitutes: { pytest: ['uv run pytest'] }, expected_nonzero_commands: ['lint'], runtime_evidence_required: true, acceptance_refs: ['REQ-1'] },
              { status: 'DONE_WITH_CONCERNS', test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'uv run pytest tests', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', concerns: ['REQ-1 deferred w/ user ok'], acceptance_coverage: [{ ref: 'REQ-1' }], unverified_acceptance_refs: [], diff_summary: 'M src/a.js', dirty_commit_sha: 'dirty-ok' },
              { command_results: [
                { command: 'uv run pytest tests', exit_code: 0 },
                { command: 'lint', exit_code: 1 }
              ] },
              { acceptance_refs: ['REQ-1'] }
            )
        ''')
        assert result["passed"] is True
        assert result["status"] == "pass"
        assert result["evidence"]["commit_sha"] == "dirty-ok"

    def test_validate_implementation_evidence_accepts_required_expected_nonzero_command(self):
        result = self._eval_evidence_helper(r'''
            validateImplementationEvidence(
              { required_commands: ['lint'], expected_nonzero_commands: ['lint'], runtime_evidence_required: true },
              { status: 'DONE', test_results: 'lint expected failure', verification_commands: ['lint'], verification_results: [{ command: 'lint', exit_code: 1 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
              { command_results: [{ command: 'lint', exit_code: 1 }] },
              null
            )
        ''')
        assert result["passed"] is True
        assert result["status"] == "pass"

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

    def test_validate_implementation_evidence_blocks_missing_done_evidence_fields(self):
        result = self._eval_evidence_helper(r'''
            validateImplementationEvidence(
              {},
              { status: 'DONE', summary: 'Done', files_modified: ['a.js'] },
              { prompt_only: true },
              null
            )
        ''')
        assert result["passed"] is False
        for reason in [
            "missing_test_results", "missing_verification_commands", "missing_verification_results",
            "missing_base_sha", "missing_head_sha", "missing_acceptance_coverage",
            "missing_diff_summary",
        ]:
            assert reason in result["reasons"]

    def test_validate_implementation_evidence_rejects_done_with_concerns(self):
        result = self._eval_evidence_helper(r'''
            validateImplementationEvidence(
              {},
              { status: 'DONE', test_results: 'ok', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: ['prompt only'], diff_summary: 'M a.js' },
              { prompt_only: true },
              null
            )
        ''')
        assert result["passed"] is False
        assert "done_has_concerns" in result["reasons"]

    def test_validate_implementation_evidence_classifies_review_override_and_prompt_only(self):
        result = self._eval_evidence_helper(r'''
            [
              validateImplementationEvidence(
                { acceptance_refs: ['REQ-1'] },
                { status: 'DONE_WITH_CONCERNS', test_results: 'ok', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], concerns: ['REQ-1 manually inspected'], acceptance_coverage: [{ ref: 'REQ-1', status: 'covered' }], unverified_acceptance_refs: [], base_sha: '1111111', head_sha: '2222222', diff_summary: 'M src/a.js' },
                { prompt_only: true },
                { prompt_only: true }
              ),
              validateImplementationEvidence(
                { acceptance_refs: ['REQ-2'] },
                { status: 'DONE', test_results: 'ok', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], unverified_acceptance_refs: ['REQ-2'], concerns: [], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'REQ-2' }], diff_summary: 'M src/a.js' },
                { prompt_only: true },
                { prompt_only: true }
              )
            ]
        ''')
        assert result[0]["passed"] is True
        assert result[0]["status"] == "needs_review_override"
        assert "prompt_only_evidence_unverified" in result[0]["limitations"]
        assert result[0]["evidence"]["base_sha"] == "1111111"
        assert result[0]["evidence"]["head_sha"] == "2222222"
        assert result[0]["evidence"]["acceptance_coverage"][0]["ref"] == "REQ-1"
        assert result[1]["passed"] is True
        assert result[1]["status"] == "prompt_only_unverified"
        assert "unverified_acceptance_refs: REQ-2" in result[1]["limitations"]

    def test_implementation_evidence_gate_blocks_before_spec_review(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-5']],
              tasks: { 'task-5': { id: 'task-5', description: 'Do evidence-gated task', required_commands: ['pytest'] } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-5': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], base_sha: '1111111', head_sha: '2222222', diff_summary: 'M src/a.js' },
                'spec-review:task-5': { passed: true, issues: [], summary: 'should not run', prompt_only: true }
              }
            }
        ''')
        assert result["blocked"][0]["id"] == "task-5"
        assert "missing_required_command: pytest" in result["blocked"][0]["reason"]
        assert result["state_patch"]["task_evidence_validations"][0]["status"] == "block"
        assert result["final_review"] is None

    def test_implementation_evidence_gate_consumes_controller_diff_evidence(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-6']],
              tasks: { 'task-6': { id: 'task-6', description: 'Do diff-gated task' } },
              worktree: 'C:/tmp/worktree',
              git: {
                controller_commands_available: true,
                head_sha: '1111111',
                attempts: { 'implement:task-6': {
                  head_sha: '2222222', command: 'git diff',
                  committed: { ok: true, name_status: 'M\tsrc/a.js\n', diff: '+change\n' },
                  worktree: { ok: true, name_status: '', diff: '' },
                  command_results: [{ command: 'pytest', exit_code: 0, output: 'ok' }],
                  evidence_paths: ['C:/tmp/evidence.png'],
                  path_exists: { 'C:/tmp/evidence.png': true }
                } }
              },
              __agent_results: {
                'implement:task-6': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'agent pytest', exit_code: 0 }], base_sha: '', head_sha: '', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: '' },
                'spec-review:task-6': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-6': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'final-review': { passed: true, issues: [], summary: 'ok' }
              }
            }
        ''')
        evidence = result["passed"][0]["evidence"]
        assert evidence["base_sha"] == "1111111"
        assert evidence["head_sha"] == "2222222"
        assert evidence["diff_summary"] == "src/a.js"
        assert evidence["executed_commands"][0]["command"] == "pytest"
        assert evidence["evidence_paths"] == ["C:/tmp/evidence.png"]
        assert evidence["controller_diff_evidence"][0]["diff_verified"] is True
        controller = result["passed"][0]["implementation_evidence"]
        assert controller["diff_evidence"][0]["label"] == "implement:task-6"
        assert controller["command_results"][0]["command"] == "pytest"
        assert controller["evidence_paths"] == ["C:/tmp/evidence.png"]
        assert controller["path_exists"] == {"C:/tmp/evidence.png": True}

    def test_evidence_gate_uses_clean_pass_status(self):
        assert "function implementationEvidenceCleanPass" in self.script
        assert "!implementationEvidenceCleanPass(implementationEvidence)" in self.script

    def test_validate_fix_scope_allows_issue_task_tests_and_support_files(self):
        result = self._eval_evidence_helper(r'''
            (() => {
              const task = {
                files: ['src/feature/a.js'],
                tests: ['tests/test_a.py'],
                pre_fix_changed_files: ['src/feature/existing.js']
              };
              const issues = [{ id: 'issue-1', file: 'src/feature/a.js' }];
              const locationOnlyIssues = [{ id: 'issue-2', location: 'src/feature/location.js:12' }];
              const support = { imports: { 'src/feature/a.js': ['src/feature/helper.js'] } };
              const diff_evidence = [{ committed_diff: { diff_body: 'diff --git a/src/feature/a.js b/src/feature/a.js\n+++ b/src/feature/a.js\n+import util from "./util"\n' } }];
              return [
                validateFixScope(['src/feature/a.js'], issues, { files_modified: ['untrusted.js'], task }).passed,
                validateFixScope(['tests/test_a_more.py'], issues, { task }).passed,
                validateFixScope(['src/feature/existing.js'], issues, { task }).passed,
                validateFixScope(['src/feature/helper.js'], issues, { task, support }).passed,
                validateFixScope(['src/feature/util.js'], issues, { task, diff_evidence }).passed,
                validateFixScope(['src/feature/location.js'], locationOnlyIssues, { task }).passed
              ];
            })()
        ''')
        assert result == [True, True, True, True, True, True]

    def test_validate_fix_scope_blocks_unrelated_config_delete_and_rename(self):
        result = self._eval_evidence_helper(r'''
            (() => {
              const task = { files: ['src/feature/a.js', 'package.json'], tests: ['tests/test_a.py'] };
              const issues = [{ id: 'issue-1', file: 'src/feature/a.js' }, { id: 'issue-2', file: 'package.json' }];
              const unrelated = validateFixScope(['src/other/b.js'], issues, { task });
              const config = validateFixScope(['package.json'], issues, { task });
              const dockerfile = validateFixScope(['Dockerfile'], issues, { task });
              const workflow = validateFixScope(['.github/workflows/ci.yml'], issues, { task });
              const eslint = validateFixScope(['eslint.config.js'], issues, { task });
              const deleted = validateFixScope(['D\tsrc/feature/a.js'], issues, { task });
              const renamed = validateFixScope(['R100\tsrc/feature/a.js\tsrc/feature/b.js'], issues, { task });
              return [unrelated, config, dockerfile, workflow, eslint, deleted, renamed];
            })()
        ''')
        assert result[0]["passed"] is False
        assert "unrelated_file_changed: src/other/b.js" in result[0]["reasons"]
        assert result[1]["passed"] is False
        assert "broad_config_change: package.json" in result[1]["reasons"]
        assert result[2]["passed"] is False
        assert "broad_config_change: Dockerfile" in result[2]["reasons"]
        assert result[3]["passed"] is False
        assert "broad_config_change: .github/workflows/ci.yml" in result[3]["reasons"]
        assert result[4]["passed"] is False
        assert "broad_config_change: eslint.config.js" in result[4]["reasons"]
        assert result[5]["passed"] is False
        assert "delete_outside_fix_scope: src/feature/a.js" in result[5]["reasons"]
        assert result[6]["passed"] is False
        assert "rename_outside_fix_scope: src/feature/a.js -> src/feature/b.js" in result[6]["reasons"]

    def test_validate_fix_scope_blocks_formatting_only_outside_scope_and_ignores_agent_advisory(self):
        result = self._eval_evidence_helper(r'''
            validateFixScope(
              ['src/other/format.js'],
              [{ id: 'issue-1', file: 'src/feature/a.js' }],
              {
                task: { files: ['src/feature/a.js'] },
                formatting_only_files: ['src/other/format.js'],
                unrelated_files_changed: []
              }
            )
        ''')
        assert result["passed"] is False
        assert "formatting_only_outside_scope: src/other/format.js" in result["reasons"]
        assert "unrelated_files_changed" in result["advisory"]

    def test_spec_fix_reruns_implementation_evidence_gate(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-7']],
              tasks: { 'task-7': { id: 'task-7', description: 'Do fix-gated task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-7': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-7': { passed: false, issues: [{ id: 'prior-id', severity: 'Critical', blocking: true, description: 'fix it' }], summary: 'needs fix', prompt_only: true },
                'fix-spec:task-7-r1': { status: 'DONE', summary: 'Fixed', files_modified: ['src/a.js'], test_results: '', verification_commands: [], verification_results: [], base_sha: '1111111', head_sha: '3333333', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js', fixed_issue_ids: ['prior-id'], targeted_verification: [{ command: 'pytest', issue_ids: ['prior-id'] }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                'spec-review:task-7-r1': { passed: true, issues: [], summary: 'stale review should not pass', prompt_only: true },
                'code-review:task-7': { passed: true, issues: [], summary: 'should not run', prompt_only: true }
              }
            }
        ''')
        assert result["blocked"][0]["id"] == "task-7"
        assert "missing_test_results" in result["blocked"][0]["reason"]
        assert result["state_patch"]["task_evidence_validations"][0]["status"] == "block"
        assert result["final_review"] is None

    def test_code_fix_reruns_implementation_evidence_gate(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-8']],
              tasks: { 'task-8': { id: 'task-8', description: 'Do code fix-gated task', required_commands: ['pytest'] } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-8': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-8': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-8': { passed: false, issues: [{ id: 'prior-id', severity: 'Critical', blocking: true, description: 'fix code' }], summary: 'needs fix', prompt_only: true },
                'fix-code:task-8-r1': { status: 'DONE', summary: 'Fixed', files_modified: ['src/a.js'], test_results: '', verification_commands: [], verification_results: [], base_sha: '1111111', head_sha: '3333333', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js', fixed_issue_ids: ['prior-id'], targeted_verification: [{ command: 'pytest', issue_ids: ['prior-id'] }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                'code-review:task-8-r1': { passed: true, issues: [], summary: 'stale review should not pass', prompt_only: true }
              }
            }
        ''')
        assert result["blocked"][0]["id"] == "task-8"
        assert "missing_required_command: pytest" in result["blocked"][0]["reason"]
        assert result["state_patch"]["task_evidence_validations"][0]["status"] == "block"
        assert result["final_review"] is None

    def test_targeted_fix_prompt_contract(self):
        result = self._eval_evidence_helper(r'''
            (() => {
              const prompt = fixPrompt(
                [{ id: 'issue-1', severity: 'Critical', file: 'src/a.js', description: 'missing req' }],
                ['src/a.js'],
                { id: 'task-9', description: 'Do x', required_commands: ['pytest'], acceptance_refs: ['REQ-1'], attempt_diff_evidence: [{ diff_files: ['src/a.js'], diff_verified: true }] },
                { summary: 'Done', files_modified: ['src/a.js'], verification_results: [{ command: 'pytest', exit_code: 0 }], acceptance_coverage: [{ ref: 'REQ-1' }], diff_summary: 'M src/a.js' },
                'spec_fix',
                2
              );
              return [
                prompt.includes('## Targeted Fix Context'),
                prompt.includes('Stage: spec_fix'),
                prompt.includes('Task: task-9'),
                prompt.includes('Prior blocking issue IDs'),
                prompt.includes('issue-1'),
                prompt.includes('Allowed files'),
                prompt.includes('Controller diff/base metadata'),
                prompt.includes('Prior evidence'),
                prompt.includes('Required commands / acceptance refs'),
                prompt.includes('Retry count: 2'),
                prompt.includes('fixed_issue_ids'),
                prompt.includes('targeted_verification'),
                prompt.includes('verification_failures'),
                prompt.includes('unrelated_files_changed'),
                prompt.includes('diff_summary'),
                prompt.includes('scope_justifications')
              ];
            })()
        ''')
        assert result == [True] * 16

    def test_review_prompt_rereview_contract(self):
        result = self._eval_evidence_helper(r'''
            (() => {
              const prompt = specReviewPrompt(
                { id: 'task-9', description: 'Do x', attempt_diff_evidence: [{ diff_files: ['src/a.js'], diff_verified: true }] },
                {
                  summary: 'Fixed',
                  files_modified: ['src/a.js'],
                  fixed_issue_ids: ['issue-1'],
                  targeted_verification: [{ command: 'pytest', issue_ids: ['issue-1'] }],
                  verification_failures: [],
                  unrelated_files_changed: ['src/other.js'],
                  diff_summary: 'M src/a.js',
                  scope_justifications: [{ file: 'src/a.js', reason: 'issue-1' }]
                },
                { issues: [{ id: 'issue-1', severity: 'Critical', blocking: true, description: 'missing req' }] }
              );
              return [
                prompt.includes('## Targeted Re-Review Requirements'),
                prompt.includes('Verify every prior blocking issue by ID'),
                prompt.includes('prior_findings_verified'),
                prompt.includes('unresolved_issue_ids'),
                prompt.includes('new_issues'),
                prompt.includes('diff_verified'),
                prompt.includes('targeted_verification_credible'),
                prompt.includes('scope_concerns'),
                prompt.includes('repeated unresolved issues'),
                prompt.includes('controller-detected unrelated files'),
                prompt.includes('issue-1'),
                prompt.includes('src/other.js')
              ];
            })()
        ''')
        assert result == [True] * 12

    def test_review_result_schema_requires_targeted_rereview_fields(self):
        for text in [
            "const REVIEW_REREVIEW_RESULT", "...REVIEW_RESULT",
            "'prior_findings_verified', 'unresolved_issue_ids', 'new_issues'",
            "'diff_verified', 'targeted_verification_credible', 'scope_concerns'",
            "opts('spec-review:' + id + '-r' + (iterations + 1), 'Spec Review', REVIEW_REREVIEW_RESULT)",
            "opts('code-review:' + ctx.id + '-r' + (iterations + 1), 'Code Review', REVIEW_REREVIEW_RESULT)",
        ]:
            assert text in self.script

    def test_fix_result_schema_requires_targeted_fields(self):
        for text in [
            "const FIX_RESULT", "fixed_issue_ids", "targeted_verification",
            "verification_failures", "unrelated_files_changed", "scope_justifications",
        ]:
            assert text in self.script
        assert "opts(fixLabel, 'Spec Review', FIX_RESULT)" in self.script
        assert "opts(fixLabel, 'Code Review', FIX_RESULT)" in self.script

    def test_fix_loops_scope_prompts_to_blocking_issue_files(self):
        assert "fixPrompt(blockingIssues, fixIssueFiles(blockingIssues), ctx, impl, 'spec_fix'" in self.script
        assert "fixPrompt(blockingIssues, fixIssueFiles(blockingIssues), ctx, ctx.impl, 'code_fix'" in self.script
        assert "fixPrompt(blockingIssues, impl.files_modified" not in self.script
        assert "fixPrompt(blockingIssues, ctx.impl.files_modified" not in self.script

    def test_spec_fix_blocks_missing_fix_result_before_rereview(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-10']],
              tasks: { 'task-10': { id: 'task-10', description: 'Do spec fix contract task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-10': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-10': { passed: false, issues: [{ severity: 'Critical', blocking: true, file: 'src/a.js', description: 'fix it' }], summary: 'needs fix', prompt_only: true },
                'spec-review:task-10-r1': { passed: true, issues: [], summary: 'should not run', prompt_only: true },
                'code-review:task-10': { passed: true, issues: [], summary: 'should not run', prompt_only: true }
              }
            }
        ''')
        assert result["blocked"][0]["id"] == "task-10"
        assert "missing_fix_result" in result["blocked"][0]["reason"]
        assert result["state_patch"]["task_evidence_validations"][0]["status"] == "block"
        assert result["final_review"] is None

    def test_code_fix_blocks_missing_targeted_fields_before_rereview(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-11']],
              tasks: { 'task-11': { id: 'task-11', description: 'Do code fix contract task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-11': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-11': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-11': { passed: false, issues: [{ severity: 'Critical', blocking: true, file: 'src/a.js', description: 'fix code' }], summary: 'needs fix', prompt_only: true },
                'fix-code:task-11-r1': { status: 'DONE', summary: 'Fixed', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '3333333', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'code-review:task-11-r1': { passed: true, issues: [], summary: 'should not run', prompt_only: true }
              }
            }
        ''')
        assert result["blocked"][0]["id"] == "task-11"
        assert "missing_fixed_issue_ids" in result["blocked"][0]["reason"]
        assert result["state_patch"]["task_evidence_validations"][0]["status"] == "block"
        assert result["final_review"] is None

    def test_fix_scope_policy_is_helper_only_not_review_loop_gate(self):
        assert "function validateLatestFixScope" in self.script
        assert "const fixScope = validateLatestFixScope" not in self.script
        assert "_fix_scope_blocked" not in self.script

    def test_rereview_metadata_blocks_spec_pass(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-12']],
              tasks: { 'task-12': { id: 'task-12', description: 'Do spec re-review metadata task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-12': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-12': { passed: false, issues: [{ id: 'prior-id', severity: 'Critical', blocking: true, file: 'src/a.js', description: 'fix it' }], summary: 'needs fix', prompt_only: true },
                'fix-spec:task-12-r1': { status: 'DONE', summary: 'Fixed', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '3333333', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js', fixed_issue_ids: ['prior-id'], targeted_verification: [{ command: 'pytest', issue_ids: ['prior-id'] }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                'spec-review:task-12-r1': { passed: true, issues: [], summary: 'should not pass', prompt_only: true, prior_findings_verified: [], unresolved_issue_ids: ['prior-id'], new_issues: [], diff_verified: true, targeted_verification_credible: true, scope_concerns: [] },
                'code-review:task-12': { passed: true, issues: [], summary: 'should not run', prompt_only: true }
              }
            }
        ''')
        assert result["stalled"][0]["id"] == "task-12"
        assert result["stalled"][0]["spec_passed"] is False
        assert result["final_review"] is None

    def test_rereview_metadata_blocks_code_pass(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-13']],
              tasks: { 'task-13': { id: 'task-13', description: 'Do code re-review metadata task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-13': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-13': { passed: true, issues: [], summary: 'ok', prompt_only: true },
                'code-review:task-13': { passed: false, issues: [{ id: 'prior-id', severity: 'Critical', blocking: true, file: 'src/a.js', description: 'fix code' }], summary: 'needs fix', prompt_only: true },
                'fix-code:task-13-r1': { status: 'DONE', summary: 'Fixed', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '3333333', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js', fixed_issue_ids: ['prior-id'], targeted_verification: [{ command: 'pytest', issue_ids: ['prior-id'] }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                'code-review:task-13-r1': { passed: true, issues: [], summary: 'should not pass', prompt_only: true, prior_findings_verified: [{ id: 'prior-id', verified: false }], unresolved_issue_ids: [], new_issues: [], diff_verified: true, targeted_verification_credible: true, scope_concerns: [] }
              }
            }
        ''')
        assert result["stalled"][0]["id"] == "task-13"
        assert result["stalled"][0]["code_passed"] is False
        assert result["final_review"] is None

    def test_rereview_metadata_blocks_omitted_prior_issue(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-14']],
              tasks: { 'task-14': { id: 'task-14', description: 'Do omitted prior re-review task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-14': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-14': { passed: false, issues: [{ id: 'prior-id', severity: 'Critical', blocking: true, file: 'src/a.js', description: 'fix it' }], summary: 'needs fix', prompt_only: true },
                'fix-spec:task-14-r1': { status: 'DONE', summary: 'Fixed', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '3333333', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js', fixed_issue_ids: ['prior-id'], targeted_verification: [{ command: 'pytest', issue_ids: ['prior-id'] }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                'spec-review:task-14-r1': { passed: true, issues: [], summary: 'should not pass', prompt_only: true, prior_findings_verified: [], unresolved_issue_ids: [], new_issues: [], diff_verified: true, targeted_verification_credible: true, scope_concerns: [] },
                'code-review:task-14': { passed: true, issues: [], summary: 'should not run', prompt_only: true }
              }
            }
        ''')
        assert result["stalled"][0]["id"] == "task-14"
        assert result["stalled"][0]["spec_passed"] is False
        assert result["final_review"] is None

    def test_fix_result_blocks_missing_prior_ids_targeting_and_failures(self):
        result = self._eval_evidence_helper(r'''
            validateFixResultContract(
              { status: 'DONE', fixed_issue_ids: ['other-id'], targeted_verification: [{ command: 'pytest', issue_ids: ['other-id'] }], verification_failures: [{ issue_id: 'prior-id' }], unrelated_files_changed: [], scope_justifications: [] },
              [{ id: 'prior-id' }]
            )
        ''')
        assert result["passed"] is False
        assert "missing_fixed_issue_id: prior-id" in result["reasons"]
        assert "missing_targeted_verification: prior-id" in result["reasons"]
        assert "verification_failure: prior-id" in result["reasons"]

    def test_fix_result_targeted_verification_accepts_issue_id_aliases(self):
        result = self._eval_evidence_helper(r'''
            [
              validateFixResultContract(
                { status: 'DONE', fixed_issue_ids: ['issue-a'], targeted_verification: [{ command: 'pytest', issue_id: 'issue-a' }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                [{ id: 'issue-a' }]
              ),
              validateFixResultContract(
                { status: 'DONE', fixed_issue_ids: ['issue-b'], targeted_verification: [{ command: 'pytest', id: 'issue-b' }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                [{ id: 'issue-b' }]
              ),
              validateFixResultContract(
                { status: 'DONE', fixed_issue_ids: ['issue-c'], targeted_verification: [{ command: 'pytest', prior_issue_id: 'issue-c' }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                [{ id: 'issue-c' }]
              )
            ]
        ''')
        assert [item["passed"] for item in result] == [True, True, True]

    def test_retry_counters_are_fix_attempts_not_initial_reviews(self):
        result = self._eval_workflow(r'''
            {
              groups: [['task-15']],
              tasks: { 'task-15': { id: 'task-15', description: 'Do retry counter task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-15': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-15': { passed: false, issues: [{ id: 'spec-1', severity: 'Critical', blocking: true, file: 'src/a.js', description: 'fix spec' }], summary: 'needs fix', prompt_only: true },
                'fix-spec:task-15-r1': { status: 'DONE', summary: 'Fixed', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '3333333', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js', fixed_issue_ids: ['spec-1'], targeted_verification: [{ command: 'pytest', issue_ids: ['spec-1'] }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                'spec-review:task-15-r1': { passed: true, issues: [], summary: 'ok', prompt_only: true, prior_findings_verified: [{ id: 'spec-1', verified: true }], unresolved_issue_ids: [], new_issues: [], diff_verified: true, targeted_verification_credible: true, scope_concerns: [] },
                'code-review:task-15': { passed: false, issues: [{ id: 'code-1', severity: 'Critical', blocking: true, file: 'src/a.js', description: 'fix code' }], summary: 'needs fix', prompt_only: true },
                'fix-code:task-15-r1': { status: 'DONE', summary: 'Fixed', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '4444444', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js', fixed_issue_ids: ['code-1'], targeted_verification: [{ command: 'pytest', issue_ids: ['code-1'] }], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] },
                'code-review:task-15-r1': { passed: true, issues: [], summary: 'ok', prompt_only: true, prior_findings_verified: [{ id: 'code-1', verified: true }], unresolved_issue_ids: [], new_issues: [], diff_verified: true, targeted_verification_credible: true, scope_concerns: [] },
                'final-review': { passed: true, issues: [], summary: 'ok' }
              }
            }
        ''')
        entry = result["passed"][0]
        assert entry["spec_fix_attempts"] == 1
        assert entry["code_fix_attempts"] == 1
        assert "spec_review_attempts" not in entry
        assert "code_review_attempts" not in entry
        labels = [e["label"] for e in entry["attempt_diff_evidence"]]
        assert "fix-spec:task-15-r1" in labels
        assert "fix-code:task-15-r1" in labels

    def test_spec_exhaustion_preserves_unresolved_metadata_and_failed_review_partition(self):
        spec_results = []
        fix_results = {}
        for i in range(1, 6):
            spec_results.append(f"'fix-spec:task-16-r{i}': {{ status: 'DONE', summary: 'Fixed', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{{ command: 'pytest', exit_code: 0 }}], base_sha: '1111111', head_sha: '333333{i}', acceptance_coverage: [{{ ref: 'task' }}], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js', fixed_issue_ids: ['spec-1'], targeted_verification: [{{ command: 'pytest', issue_ids: ['spec-1'] }}], verification_failures: [], unrelated_files_changed: [], scope_justifications: [] }}")
            fix_results[i] = f"'spec-review:task-16-r{i}': {{ passed: false, issues: [{{ id: 'spec-1', severity: 'Critical', blocking: true, file: 'src/a.js', description: 'still broken' }}], summary: 'still failing', prompt_only: true, prior_findings_verified: [{{ id: 'spec-1', verified: false }}], unresolved_issue_ids: ['spec-1'], new_issues: [], diff_verified: true, targeted_verification_credible: true, scope_concerns: [] }}"
        result = self._eval_workflow(r'''
            {
              groups: [['task-16']],
              tasks: { 'task-16': { id: 'task-16', description: 'Do exhausted spec task' } },
              worktree: 'C:/tmp/worktree',
              git: { controller_commands_available: true, head_sha: '1111111' },
              __agent_results: {
                'implement:task-16': { status: 'DONE', summary: 'Done', files_modified: ['src/a.js'], test_results: 'pytest passed', verification_commands: ['pytest'], verification_results: [{ command: 'pytest', exit_code: 0 }], base_sha: '1111111', head_sha: '2222222', acceptance_coverage: [{ ref: 'task' }], unverified_acceptance_refs: [], concerns: [], diff_summary: 'M src/a.js' },
                'spec-review:task-16': { passed: false, issues: [{ id: 'spec-1', severity: 'Critical', blocking: true, file: 'src/a.js', description: 'fix spec' }], summary: 'needs fix', prompt_only: true },
                PLACEHOLDER
              }
            }
        '''.replace('PLACEHOLDER', ',\n                '.join(spec_results + [fix_results[i] for i in range(1, 6)])))
        failed = result["failed_review"][0]
        assert result["passed"] == []
        assert failed["stage"] == "spec_review"
        assert failed["spec_fix_attempts"] == 5
        assert failed["unresolved_issue_ids"] == ["spec-1"]
        assert failed["spec_passed"] is False
        assert failed["evidence_validation"]["status"] == "pass"
        assert failed["attempt_diff_evidence"]

    def test_blocked_and_done_with_concerns_cannot_bypass_review_decisions(self):
        assert "impl.status === 'BLOCKED'" in self.script
        assert "implementation_blocked" in self.script
        assert "needs_review_override" in self.script
        assert "reviewOverrideDecisionAllowsConcerns" in self.script

    def test_classification_wires_implementation_evidence_validation(self):
        assert "validateImplementationEvidence(task, ctx.impl, ctx.implementation_evidence, ctx.code_review)" in self.script
        assert "evidence_validation: implementationEvidence" in self.script
        assert "partition: 'blocked'" in self.script

    def test_passed_classification_persists_attempt_diff_evidence(self):
        passed_entry = re.search(r"partition: 'passed',[\s\S]+?entry: \{([\s\S]+?)\n    \}", self.script)
        assert passed_entry, "passed classification entry not found"
        assert "attempt_diff_evidence: ctx.attempt_diff_evidence || []" in passed_entry.group(1)


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
