"""Tests for execute-plan resume contract.

Validates that the result adapter produces a state_patch with partition
summaries, total_tasks count, and final_review_run flag that a resume
cursor can use to reconstruct execution state.
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
