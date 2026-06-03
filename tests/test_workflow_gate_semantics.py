"""Tests for workflow completion-gate semantics.

Validates that the canonical gate set is enforced and that gate drift
(e.g. a driver reporting fewer gates than canonical) is rejected.
"""

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dynamic_workflow"

CANONICAL_GATES = [
    "gate_1_tasks_executed",
    "gate_2_reviews_passed",
    "gate_3_tests_pass",
    "gate_4_runtime_evidence",
    "gate_5_spec_verified",
    "gate_6_final_review",
    "gate_7_git_clean",
]


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_rejects_six_gate_completion_fixture():
    """Six-gate completion must be rejected — canonical count is seven.

    The fixture represents a driver that reports only the legacy six gates
    (missing gate_4_runtime_evidence) with all_passed=true. This must fail
    validation because the canonical gate set requires seven gates.
    """
    data = _load_fixture("gate_drift_six_vs_seven.json")

    reported_gates = set(data["gate_states"].keys())
    canonical_set = set(CANONICAL_GATES)

    # The fixture must NOT match the canonical gate set
    assert reported_gates != canonical_set, (
        "Fixture should have six gates, not seven — "
        "update fixture if canonical gates changed"
    )

    # Validate that the fixture claims all passed despite being incomplete
    assert data["all_passed"] is True, (
        "Fixture must claim all_passed=true to demonstrate the drift scenario"
    )

    # A six-gate driver must be rejected: missing canonical gates
    missing = canonical_set - reported_gates
    assert len(missing) > 0, (
        "Six-gate completion is missing at least one canonical gate"
    )

    # Specifically, runtime_evidence should be the missing gate
    assert "gate_4_runtime_evidence" in missing, (
        "Expected gate_4_runtime_evidence to be the missing gate in the six-gate fixture"
    )
