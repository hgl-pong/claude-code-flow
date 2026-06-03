"""Tests for workflow resume contract and state-writer integration.

Covers two areas:
1. execute-plan resume contract (state_patch, partitions, evidence propagation)
2. full-auto-pipeline state-writer integration (flowState, phase events,
   STOPPED_ASK_USER, gate cursor, enriched final return)
"""

import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills" / "workflow-driven-development"
EXECUTE_PLAN = SKILLS_DIR / "execute-plan.workflow.js"

RESULT_PARTITIONS = ["passed", "completed", "blocked", "stalled", "failed_review", "needs_escalation"]


def _read_script() -> str:
    assert EXECUTE_PLAN.exists(), f"Script not found: {EXECUTE_PLAN}"
    return EXECUTE_PLAN.read_text(encoding="utf-8")


class TestStatePatchStructure:
    """Contract: state_patch has all required fields for resume."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script()

    def test_state_patch_returned(self):
        """The return value must include state_patch."""
        assert "state_patch" in self.script

    def test_state_patch_has_all_partition_keys(self):
        """state_patch.partitions must list IDs for each of the 6 partitions."""
        for p in RESULT_PARTITIONS:
            assert f"'{p}'" in self.script or f'"{p}"' in self.script

    def test_state_patch_total_tasks(self):
        """state_patch.total_tasks must match the number of input tasks."""
        assert "total_tasks" in self.script
        assert "totalTasks" in self.script

    def test_state_patch_final_review_run(self):
        """state_patch.final_review_run must indicate whether final review ran."""
        assert "final_review_run" in self.script


class TestResultAdapterReturnShape:
    """Contract: the return value has all 6 partition arrays plus metadata."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script()

    def test_return_has_passed(self):
        assert "passed:" in self.script or "passed =" in self.script

    def test_return_has_completed(self):
        assert "completed:" in self.script or "completed =" in self.script

    def test_return_has_blocked(self):
        assert "blocked:" in self.script or "blocked =" in self.script

    def test_return_has_stalled(self):
        assert "stalled:" in self.script or "stalled =" in self.script

    def test_return_has_failed_review(self):
        assert "failed_review:" in self.script or "failed_review =" in self.script

    def test_return_has_needs_escalation(self):
        assert "needs_escalation:" in self.script or "needs_escalation =" in self.script

    def test_return_has_final_review(self):
        assert "final_review:" in self.script or "final_review =" in self.script


class TestResumeCursorCanReconstruct:
    """Contract: a resume cursor can reconstruct execution state from state_patch.

    This tests the data shape, not runtime behavior.
    """

    def test_simulated_state_patch_has_required_fields(self):
        """Simulated state_patch must be reconstructable."""
        state_patch = {
            "partitions": {
                "passed": ["task-1", "task-2"],
                "completed": ["task-1", "task-2"],
                "blocked": [],
                "stalled": [],
                "failed_review": ["task-3"],
                "needs_escalation": [],
            },
            "total_tasks": 3,
            "final_review_run": False,
        }

        # Can determine if all tasks completed
        all_completed = (
            len(state_patch["partitions"]["completed"]) == state_patch["total_tasks"]
        )
        assert all_completed is False  # task-3 is in failed_review

        # Can determine which tasks to retry
        retryable = (
            state_patch["partitions"]["failed_review"]
            + state_patch["partitions"]["stalled"]
            + state_patch["partitions"]["blocked"]
        )
        assert retryable == ["task-3"]

        # Can determine if final review was skipped
        assert state_patch["final_review_run"] is False

    def test_all_passed_state_patch(self):
        """When all tasks passed, final_review_run should be True."""
        state_patch = {
            "partitions": {
                "passed": ["task-1", "task-2"],
                "completed": ["task-1", "task-2"],
                "blocked": [],
                "stalled": [],
                "failed_review": [],
                "needs_escalation": [],
            },
            "total_tasks": 2,
            "final_review_run": True,
        }

        all_completed = (
            len(state_patch["partitions"]["completed"]) == state_patch["total_tasks"]
        )
        other_empty = all(
            len(state_patch["partitions"][p]) == 0
            for p in ["blocked", "stalled", "failed_review", "needs_escalation"]
        )
        assert all_completed is True
        assert other_empty is True
        assert state_patch["final_review_run"] is True

    def test_completed_always_equals_passed(self):
        """Invariant: completed IDs == passed IDs."""
        state_patch = {
            "partitions": {
                "passed": ["task-1"],
                "completed": ["task-1"],
                "blocked": ["task-2"],
                "stalled": [],
                "failed_review": [],
                "needs_escalation": [],
            },
            "total_tasks": 2,
            "final_review_run": False,
        }

        assert state_patch["partitions"]["completed"] == state_patch["partitions"]["passed"]

    def test_every_task_in_exactly_one_partition(self):
        """Invariant: union of all partition ID lists == all task IDs, no overlap."""
        state_patch = {
            "partitions": {
                "passed": ["task-1"],
                "completed": ["task-1"],
                "blocked": ["task-2"],
                "stalled": [],
                "failed_review": ["task-3"],
                "needs_escalation": [],
            },
            "total_tasks": 3,
            "final_review_run": False,
        }

        # completed is a copy of passed, so exclude it from overlap check
        canonical_partitions = ["passed", "blocked", "stalled", "failed_review", "needs_escalation"]
        all_ids = []
        for p in canonical_partitions:
            all_ids.extend(state_patch["partitions"][p])

        # Each ID appears exactly once in canonical partitions
        assert len(all_ids) == len(set(all_ids))
        # All tasks accounted for
        assert len(all_ids) == state_patch["total_tasks"]

    def test_no_failed_unreviewed_in_passed(self):
        """Invariant: passed must never contain failed or unreviewed tasks."""
        state_patch = {
            "partitions": {
                "passed": ["task-1"],
                "completed": ["task-1"],
                "blocked": ["task-2"],
                "stalled": [],
                "failed_review": ["task-3"],
                "needs_escalation": [],
            },
            "total_tasks": 3,
            "final_review_run": False,
        }

        passed = set(state_patch["partitions"]["passed"])
        failed = set(state_patch["partitions"]["failed_review"])
        blocked = set(state_patch["partitions"]["blocked"])
        escalated = set(state_patch["partitions"]["needs_escalation"])

        assert passed.isdisjoint(failed)
        assert passed.isdisjoint(blocked)
        assert passed.isdisjoint(escalated)


class TestEvidencePropagation:
    """Contract: passed tasks propagate evidence fields from impl."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script()

    def test_evidence_extraction_function_exists(self):
        assert "function extractEvidence" in self.script

    def test_evidence_includes_commit_sha(self):
        assert "commit_sha" in self.script

    def test_evidence_includes_test_results(self):
        assert "test_results" in self.script

    def test_evidence_includes_verification_commands(self):
        assert "verification_commands" in self.script

    def test_evidence_includes_evidence_paths(self):
        assert "evidence_paths" in self.script

    def test_evidence_includes_concerns(self):
        assert "concerns" in self.script

    def test_evidence_includes_files_modified(self):
        assert "files_modified" in self.script

    def test_passed_entry_has_evidence(self):
        """classifyTaskResult for passed tasks must include evidence."""
        assert "evidence:" in self.script or "evidence =" in self.script


# ── full-auto-pipeline state-writer integration tests ──────────────────

FULL_AUTO = SKILLS_DIR / "full-auto-pipeline.workflow.js"


def _read_full_auto() -> str:
    assert FULL_AUTO.exists(), f"Script not found: {FULL_AUTO}"
    return FULL_AUTO.read_text(encoding="utf-8")


class TestFullAutoStateWriterArgs:
    """Contract: full-auto-pipeline accepts state-writer integration args."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_state_file_arg_destructured(self):
        assert "state_file" in self.script
        assert re.search(r"state_file[,}\s]", self.script)

    def test_audit_dir_arg_destructured(self):
        assert "audit_dir" in self.script
        assert re.search(r"audit_dir[,}\s]", self.script)

    def test_evidence_dir_arg_destructured(self):
        assert "evidence_dir" in self.script
        assert re.search(r"evidence_dir[,}\s]", self.script)

    def test_resume_from_arg_destructured(self):
        assert "resume_from" in self.script
        assert re.search(r"resume_from[,}\s]", self.script)

    def test_retry_policy_arg_destructured(self):
        assert "retry_policy" in self.script
        assert re.search(r"retry_policy[,}\s]", self.script)

    def test_allowed_escalation_models_arg(self):
        assert "allowed_escalation_models" in self.script

    def test_allow_commit_arg(self):
        assert "allow_commit" in self.script

    def test_flow_state_script_path_arg(self):
        assert "flow_state_script_path" in self.script


class TestFullAutoFlowStateHelper:
    """Contract: flowState helper function exists with correct signature."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_flow_state_function_exists(self):
        assert "async function flowState" in self.script

    def test_flow_state_accepts_cmd_and_payload(self):
        assert "flowState(cmd, payload)" in self.script

    def test_flow_state_noop_when_no_script(self):
        assert "if (!flowStateScriptPath)" in self.script
        assert "{ ok: true }" in self.script

    def test_flow_state_calls_workflow(self):
        assert "workflow({ scriptPath: flowStateScriptPath }" in self.script

    def test_flow_state_tracks_revision(self):
        assert "currentRevision" in self.script

    def test_flow_state_passes_state_file(self):
        assert "state_file: state_file" in self.script

    def test_flow_state_passes_expected_revision(self):
        assert "expected_revision: currentRevision" in self.script


class TestFullAutoPhaseTransitionEvents:
    """Contract: every phase records start event and completion update."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_scope_phase_start_event(self):
        assert "flowState('event', { type: 'phase_start', phase: 'scope' })" in self.script

    def test_scope_phase_completion(self):
        assert "flowState('update', { phase: 'scope'" in self.script

    def test_research_phase_start_event(self):
        assert "flowState('event', { type: 'phase_start', phase: 'research' })" in self.script

    def test_research_phase_completion(self):
        assert "flowState('update', { phase: 'research' })" in self.script

    def test_synthesize_spec_phase_start(self):
        assert "flowState('event', { type: 'phase_start', phase: 'synthesize_spec' })" in self.script

    def test_synthesize_spec_phase_completion(self):
        assert "flowState('update', { phase: 'synthesize_spec', spec_path:" in self.script

    def test_review_spec_phase_start(self):
        assert "flowState('event', { type: 'phase_start', phase: 'review_spec' })" in self.script

    def test_write_plan_phase_start(self):
        assert "flowState('event', { type: 'phase_start', phase: 'write_plan' })" in self.script

    def test_write_plan_phase_completion_with_path(self):
        assert "flowState('update', { phase: 'write_plan', plan_path:" in self.script

    def test_parse_plan_phase_start(self):
        assert "flowState('event', { type: 'phase_start', phase: 'parse_plan' })" in self.script

    def test_execute_phase_start(self):
        assert "flowState('event', { type: 'phase_start', phase: 'execute' })" in self.script

    def test_gates_phase_start(self):
        assert "flowState('event', { type: 'phase_start', phase: 'gates' })" in self.script

    def test_spec_path_recorded_after_synthesize(self):
        pattern = r"flowState\('update',\s*\{\s*phase:\s*'synthesize_spec',\s*spec_path:"
        assert re.search(pattern, self.script)

    def test_plan_path_recorded_after_write(self):
        pattern = r"flowState\('update',\s*\{\s*phase:\s*'write_plan',\s*plan_path:"
        assert re.search(pattern, self.script)


class TestFullAutoStoppedAskUser:
    """Contract: STOPPED_ASK_USER returned when review cap exhausted."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_stopped_ask_user_status(self):
        assert "status: 'STOPPED_ASK_USER'" in self.script

    def test_stopped_ask_user_returns_resume_cursor(self):
        assert "resume_cursor:" in self.script

    def test_stopped_ask_user_returns_audit_events(self):
        assert "audit_events: auditEvents" in self.script

    def test_stopped_ask_user_returns_state_file(self):
        assert "state_file: state_file" in self.script

    def test_stopped_ask_user_returns_evidence_dir(self):
        assert "evidence_dir: evidence_dir" in self.script

    def test_stopped_ask_user_in_spec_review(self):
        assert "stopped_ask_user" in self.script
        count = self.script.count("STOPPED_ASK_USER")
        assert count >= 2, f"Expected at least 2 STOPPED_ASK_USER, got {count}"

    def test_review_loop_uses_review_retry_cap(self):
        assert "specIterations < REVIEW_RETRY_CAP" in self.script
        assert "planIterations < REVIEW_RETRY_CAP" in self.script

    def test_review_retry_cap_from_retry_policy(self):
        assert "retry_policy" in self.script
        assert "review_cap" in self.script


class TestFullAutoGateCursorTracking:
    """Contract: gate cursor tracked and written to state."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_gate_cursor_variable_initialized(self):
        assert "let gateCursor = 0" in self.script

    def test_gate_cursor_updated_after_each_gate(self):
        for i in range(1, 8):
            assert f"gateCursor = {i}" in self.script, f"Missing gateCursor = {i}"

    def test_gate_state_written_after_each_gate(self):
        count = self.script.count("gate_states: gates")
        assert count >= 7, f"Expected at least 7 gate_states updates, got {count}"

    def test_resume_cursor_written_after_each_gate(self):
        count = self.script.count("gate_cursor: gateCursor")
        assert count >= 7, f"Expected at least 7 gate_cursor updates, got {count}"


class TestFullAutoEnrichedFinalReturn:
    """Contract: final return includes state_file, audit_events, evidence_dir, resume_cursor."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_return_includes_state_file(self):
        pattern = r"state_file:\s*state_file\s*\|\|\s*null"
        assert re.search(pattern, self.script)

    def test_return_includes_audit_events(self):
        assert "audit_events: auditEvents" in self.script

    def test_return_includes_evidence_dir(self):
        pattern = r"evidence_dir:\s*evidence_dir\s*\|\|\s*null"
        assert re.search(pattern, self.script)

    def test_return_includes_resume_cursor(self):
        assert "resume_cursor: finalResumeCursor" in self.script

    def test_final_resume_cursor_has_gate_cursor(self):
        assert "gate_cursor: gateCursor" in self.script

    def test_final_resume_cursor_has_spec_path(self):
        assert "spec_path: spec.spec_path" in self.script

    def test_final_resume_cursor_has_plan_path(self):
        assert "plan_path: planResult.plan_path" in self.script

    def test_finalize_status_done_on_success(self):
        assert "'DONE'" in self.script

    def test_finalize_status_blocked_on_failure(self):
        assert "'BLOCKED_ESCALATING'" in self.script

    def test_run_complete_event(self):
        assert "type: 'run_complete'" in self.script

    def test_audit_events_collected(self):
        assert "const auditEvents = []" in self.script
        assert "auditEvents.push(" in self.script


class TestFullAutoMetaSchema:
    """Contract: meta object includes args_schema and result_schema."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_args_schema_exists(self):
        assert "args_schema" in self.script

    def test_result_schema_exists(self):
        assert "result_schema" in self.script

    def test_result_schema_has_state_file(self):
        pattern = r"result_schema.*state_file"
        assert re.search(pattern, self.script, re.DOTALL)

    def test_result_schema_has_audit_events(self):
        pattern = r"result_schema.*audit_events"
        assert re.search(pattern, self.script, re.DOTALL)

    def test_result_schema_has_evidence_dir(self):
        pattern = r"result_schema.*evidence_dir"
        assert re.search(pattern, self.script, re.DOTALL)

    def test_result_schema_has_resume_cursor(self):
        pattern = r"result_schema.*resume_cursor"
        assert re.search(pattern, self.script, re.DOTALL)
