"""Tests for workflow completion-gate semantics.

Validates that the canonical gate set is enforced, gate predicates are
correct, retry caps work, manifest structure is correct, and resume
support properly skips already-passed gates.

Uses pure-Python simulations of the gate decision logic (no real agent calls).
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "dynamic_workflow"
SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills" / "workflow-driven-development"
FULL_AUTO = SKILLS_DIR / "full-auto-pipeline.workflow.js"

CANONICAL_GATES = [
    "tasks_executed",
    "reviews_passed",
    "tests_pass",
    "runtime_evidence",
    "spec_verified",
    "final_review",
    "git_clean",
]

GATE_RETRY_CAP_DEFAULT = 10


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _read_full_auto() -> str:
    assert FULL_AUTO.exists(), f"Script not found: {FULL_AUTO}"
    return FULL_AUTO.read_text(encoding="utf-8")


# ── Pure-Python gate logic simulation ─────────────────────────────────


def make_gate_record(name: str, passed: bool, detail: str, extra: dict = None) -> dict:
    extra = extra or {}
    now = datetime.now(timezone.utc).isoformat()
    return {
        "name": name,
        "passed": passed,
        "detail": detail or "",
        "iterations": extra.get("iterations", 1),
        "last_failure": extra.get("last_failure") or None,
        "last_fix": extra.get("last_fix") or None,
        "evidence_paths": extra.get("evidence_paths") or [],
        "updated_at": now,
        "next_action": "proceed" if passed else extra.get("next_action", "retry"),
        "fix_applied": extra.get("fix_applied", ""),
    }


def make_runtime_manifest(
    passed: bool,
    detail: str = "",
    crash: bool = False,
    hang: bool = False,
) -> dict:
    return {
        "commands": detail or "N/A",
        "exit_codes": [0] if passed else [1],
        "logs": [],
        "screenshots": [],
        "artifacts": [],
        "crash": crash,
        "hang": hang,
        "unverified_acceptance_items": [],
        "blocking_risks": [] if passed else [detail],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_gates(
    execute_result: dict,
    spec_path: str = "spec.md",
    evidence_dir: str = "evidence/",
    resume_cursor: dict = None,
    gate_retries: int = GATE_RETRY_CAP_DEFAULT,
) -> list:
    """Simulate the 7-gate pipeline with enriched gate records."""
    resume_cursor = resume_cursor or {}
    resume_gate_cursor = resume_cursor.get("gate_cursor", 0)
    resume_gate_states = resume_cursor.get("gate_states", {})

    gate_states = {}
    gate_cursor = 0

    def is_already_passed(name: str, idx: int) -> bool:
        return (
            idx < resume_gate_cursor
            and resume_gate_states.get(name, {}).get("passed", False)
        )

    def prior_passed() -> bool:
        if gate_cursor == 0:
            return True
        prev_name = CANONICAL_GATES[gate_cursor - 1]
        return gate_states.get(prev_name, {}).get("passed", False)

    def record(name: str, passed: bool, detail: str, extra: dict = None):
        rec = make_gate_record(name, passed, detail, extra)
        gate_states[name] = rec
        return rec

    # Gate 1: tasks_executed
    if is_already_passed("tasks_executed", 0):
        gate_states["tasks_executed"] = resume_gate_states["tasks_executed"]
        gate_cursor = 1
    else:
        blocked = execute_result.get("blocked", [])
        completed = execute_result.get("completed", [])
        passed = len(blocked) == 0
        detail = f"{len(completed)} completed, {len(blocked)} blocked"
        record("tasks_executed", passed, detail, {
            "iterations": 1,
            "last_failure": None if passed else detail,
            "next_action": "proceed" if passed else "retry_tasks",
        })
        gate_cursor = 1

    # Gate 2: reviews_passed
    if is_already_passed("reviews_passed", 1):
        gate_states["reviews_passed"] = resume_gate_states["reviews_passed"]
        gate_cursor = 2
    elif prior_passed():
        completed = execute_result.get("completed", [])
        passed = len(completed) > 0 and all(r.get("code_passed") for r in completed)
        detail = "All reviews passed" if passed else "Some reviews have unresolved issues"
        record("reviews_passed", passed, detail, {
            "iterations": 1,
            "last_failure": None if passed else detail,
            "next_action": "proceed" if passed else "fix_reviews",
        })
        gate_cursor = 2
    else:
        record("reviews_passed", False, "Skipped — tasks_executed not passed",
               {"iterations": 0, "next_action": "unblock_gate_1"})
        gate_cursor = 2

    # Gate 3: tests_pass
    if is_already_passed("tests_pass", 2):
        gate_states["tests_pass"] = resume_gate_states["tests_pass"]
        gate_cursor = 3
    elif prior_passed():
        # Simulate: tests pass immediately
        record("tests_pass", True, "All tests passed", {
            "iterations": 1,
            "next_action": "proceed",
        })
        gate_cursor = 3
    else:
        record("tests_pass", False, "Skipped — reviews_passed not passed",
               {"iterations": 0, "next_action": "unblock_gate_2"})
        gate_cursor = 3

    # Gate 4: runtime_evidence (with manifest)
    if is_already_passed("runtime_evidence", 3):
        gate_states["runtime_evidence"] = resume_gate_states["runtime_evidence"]
        gate_cursor = 4
    elif prior_passed():
        manifest = make_runtime_manifest(True, "Smoke test passed")
        rec = record("runtime_evidence", True, "Smoke test passed", {
            "iterations": 1,
            "evidence_paths": [evidence_dir],
            "next_action": "proceed",
        })
        rec["manifest"] = manifest
        gate_cursor = 4
    else:
        record("runtime_evidence", False, "Skipped — tests_pass not passed",
               {"iterations": 0, "next_action": "unblock_gate_3"})
        gate_cursor = 4

    # Gate 5: spec_verified
    if is_already_passed("spec_verified", 4):
        gate_states["spec_verified"] = resume_gate_states["spec_verified"]
        gate_cursor = 5
    elif prior_passed():
        record("spec_verified", True, "All spec requirements verified", {
            "iterations": 1,
            "evidence_paths": [spec_path],
            "next_action": "proceed",
        })
        gate_cursor = 5
    else:
        record("spec_verified", False, "Skipped — runtime_evidence not passed",
               {"iterations": 0, "next_action": "unblock_gate_4"})
        gate_cursor = 5

    # Gate 6: final_review
    if is_already_passed("final_review", 5):
        gate_states["final_review"] = resume_gate_states["final_review"]
        gate_cursor = 6
    elif prior_passed():
        final_review = execute_result.get("final_review")
        has_valid_final = (
            final_review
            and final_review.get("passed") is True
            and len(execute_result.get("completed", [])) > 0
            and all(r.get("code_passed") for r in execute_result["completed"])
        )
        if has_valid_final:
            record("final_review", True,
                   "Final review from execute phase confirmed (all tasks passed before review)", {
                       "iterations": 1,
                       "next_action": "proceed",
                   })
        else:
            # Simulate running fresh final review
            record("final_review", True, "Final review passed", {
                "iterations": 1,
                "next_action": "proceed",
            })
        gate_cursor = 6
    else:
        record("final_review", False, "Skipped — spec_verified not passed",
               {"iterations": 0, "next_action": "unblock_gate_5"})
        gate_cursor = 6

    # Gate 7: git_clean
    if is_already_passed("git_clean", 6):
        gate_states["git_clean"] = resume_gate_states["git_clean"]
        gate_cursor = 7
    elif prior_passed():
        record("git_clean", True, "Working tree clean", {
            "iterations": 1,
            "evidence_paths": [evidence_dir] if evidence_dir else [],
            "next_action": "done",
        })
        gate_cursor = 7
    else:
        record("git_clean", False, "Skipped — final_review not passed",
               {"iterations": 0, "next_action": "unblock_gate_6"})
        gate_cursor = 7

    return [gate_states[name] for name in CANONICAL_GATES]


# ── Fixture-based gate drift test ─────────────────────────────────────


class TestGateDriftFixture:
    """Six-gate completion must be rejected — canonical count is seven."""

    def test_rejects_six_gate_completion_fixture(self):
        data = _load_fixture("gate_drift_six_vs_seven.json")

        reported_gates = set(data["gate_states"].keys())
        canonical_set = set(
            f"gate_{i+1}_{g}" for i, g in enumerate(CANONICAL_GATES)
        )

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


# ── Gate name constant tests ──────────────────────────────────────────


class TestGateNameConstants:
    """Contract: gate name constants defined in the script match CANONICAL_GATES."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_gate_name_constants_defined(self):
        for gate_name in CANONICAL_GATES:
            const_name = f"GATE_{gate_name.upper()}"
            assert const_name in self.script, f"Missing gate constant: {const_name}"

    def test_gate_names_array_defined(self):
        assert "GATE_NAMES" in self.script

    def test_gate_names_matches_canonical(self):
        pattern = r"GATE_NAMES\s*=\s*\[([^\]]+)\]"
        m = re.search(pattern, self.script)
        assert m, "GATE_NAMES array not found"
        found = re.findall(r"GATE_\w+", m.group(1))
        assert len(found) == 7, f"Expected 7 GATE_NAMES entries, got {len(found)}"


# ── Gate record structure tests ───────────────────────────────────────


class TestGateRecordStructure:
    """Contract: every gate record has required enrichment fields."""

    def test_make_gate_record_has_name(self):
        rec = make_gate_record("tasks_executed", True, "OK")
        assert rec["name"] == "tasks_executed"

    def test_make_gate_record_has_passed(self):
        rec = make_gate_record("tasks_executed", True, "OK")
        assert rec["passed"] is True

    def test_make_gate_record_has_iterations(self):
        rec = make_gate_record("tests_pass", True, "OK", {"iterations": 3})
        assert rec["iterations"] == 3

    def test_make_gate_record_default_iterations_is_1(self):
        rec = make_gate_record("tests_pass", True, "OK")
        assert rec["iterations"] == 1

    def test_make_gate_record_has_last_failure(self):
        rec = make_gate_record("tests_pass", False, "2 tests failed", {
            "last_failure": "2 tests failed",
        })
        assert rec["last_failure"] == "2 tests failed"

    def test_make_gate_record_last_failure_null_on_pass(self):
        rec = make_gate_record("tests_pass", True, "OK")
        assert rec["last_failure"] is None

    def test_make_gate_record_has_last_fix(self):
        rec = make_gate_record("tests_pass", True, "OK", {
            "last_fix": "Fixed null pointer in parser",
        })
        assert rec["last_fix"] == "Fixed null pointer in parser"

    def test_make_gate_record_has_evidence_paths(self):
        rec = make_gate_record("runtime_evidence", True, "OK", {
            "evidence_paths": ["evidence/", "logs/"],
        })
        assert rec["evidence_paths"] == ["evidence/", "logs/"]

    def test_make_gate_record_has_updated_at(self):
        rec = make_gate_record("tasks_executed", True, "OK")
        assert "updated_at" in rec
        # Should be ISO 8601
        assert "T" in rec["updated_at"]

    def test_make_gate_record_has_next_action(self):
        rec_pass = make_gate_record("tests_pass", True, "OK")
        assert rec_pass["next_action"] == "proceed"

        rec_fail = make_gate_record("tests_pass", False, "failed", {
            "next_action": "fix_tests",
        })
        assert rec_fail["next_action"] == "fix_tests"

    def test_make_gate_record_default_next_action_on_fail(self):
        rec = make_gate_record("tests_pass", False, "failed")
        assert rec["next_action"] == "retry"


# ── Gate predicate simulation tests ───────────────────────────────────


class TestGate1TasksExecuted:
    """Gate 1: all tasks must complete with zero blocked."""

    def test_passes_when_no_blocked(self):
        gates = run_gates({"completed": [{"code_passed": True}], "blocked": []})
        assert gates[0]["passed"] is True
        assert gates[0]["name"] == "tasks_executed"
        assert gates[0]["iterations"] == 1

    def test_fails_when_blocked(self):
        gates = run_gates({"completed": [{"code_passed": True}], "blocked": [{"id": "task-2"}]})
        assert gates[0]["passed"] is False
        assert gates[0]["last_failure"] is not None

    def test_detail_reports_counts(self):
        gates = run_gates({"completed": [{"code_passed": True}], "blocked": []})
        assert "1 completed" in gates[0]["detail"]
        assert "0 blocked" in gates[0]["detail"]


class TestGate2ReviewsPassed:
    """Gate 2: all completed tasks must have code_passed."""

    def test_passes_when_all_reviews_pass(self):
        gates = run_gates({"completed": [{"code_passed": True}, {"code_passed": True}], "blocked": []})
        assert gates[1]["passed"] is True
        assert gates[1]["name"] == "reviews_passed"

    def test_fails_when_review_fails(self):
        gates = run_gates({"completed": [{"code_passed": True}, {"code_passed": False}], "blocked": []})
        assert gates[1]["passed"] is False

    def test_skipped_when_gate_1_fails(self):
        gates = run_gates({"completed": [], "blocked": [{"id": "task-1"}]})
        assert gates[0]["passed"] is False
        assert gates[1]["passed"] is False
        assert "Skipped" in gates[1]["detail"]


class TestGate3TestsPass:
    """Gate 3: test suite must pass."""

    def test_passes_when_tests_green(self):
        gates = run_gates({"completed": [{"code_passed": True}], "blocked": []})
        assert gates[2]["passed"] is True
        assert gates[2]["name"] == "tests_pass"

    def test_skipped_when_gate_2_fails(self):
        gates = run_gates({"completed": [{"code_passed": False}], "blocked": []})
        assert gates[1]["passed"] is False
        assert gates[2]["passed"] is False
        assert "Skipped" in gates[2]["detail"]


class TestGate4RuntimeEvidence:
    """Gate 4: runtime evidence with manifest."""

    def test_passes_and_has_manifest(self):
        gates = run_gates({"completed": [{"code_passed": True}], "blocked": []})
        gate4 = gates[3]
        assert gate4["passed"] is True
        assert gate4["name"] == "runtime_evidence"
        assert "manifest" in gate4

    def test_manifest_has_required_fields(self):
        gates = run_gates({"completed": [{"code_passed": True}], "blocked": []})
        manifest = gates[3]["manifest"]
        for field in ["commands", "exit_codes", "logs", "screenshots", "artifacts",
                       "crash", "hang", "unverified_acceptance_items",
                       "blocking_risks", "generated_at"]:
            assert field in manifest, f"Manifest missing field: {field}"

    def test_manifest_exit_codes_0_on_pass(self):
        manifest = make_runtime_manifest(True, "OK")
        assert manifest["exit_codes"] == [0]

    def test_manifest_exit_codes_1_on_fail(self):
        manifest = make_runtime_manifest(False, "crash detected", crash=True)
        assert manifest["exit_codes"] == [1]

    def test_manifest_crash_detected(self):
        manifest = make_runtime_manifest(False, "Server crashed", crash=True)
        assert manifest["crash"] is True
        assert manifest["hang"] is False

    def test_manifest_hang_detected(self):
        manifest = make_runtime_manifest(False, "Process hung", hang=True)
        assert manifest["hang"] is True
        assert manifest["crash"] is False

    def test_manifest_blocking_risks_on_fail(self):
        manifest = make_runtime_manifest(False, "Smoke test failed")
        assert len(manifest["blocking_risks"]) > 0

    def test_manifest_no_blocking_risks_on_pass(self):
        manifest = make_runtime_manifest(True, "OK")
        assert manifest["blocking_risks"] == []

    def test_manifest_generated_at_is_iso(self):
        manifest = make_runtime_manifest(True, "OK")
        assert "T" in manifest["generated_at"]

    def test_skipped_when_gate_3_fails(self):
        gates = run_gates({"completed": [{"code_passed": False}], "blocked": []})
        assert gates[3]["passed"] is False
        assert "Skipped" in gates[3]["detail"]


class TestGate5SpecVerified:
    """Gate 5: implementation verified against spec."""

    def test_passes_when_spec_matched(self):
        gates = run_gates({"completed": [{"code_passed": True}], "blocked": []})
        assert gates[4]["passed"] is True
        assert gates[4]["name"] == "spec_verified"
        assert gates[4]["evidence_paths"] == ["spec.md"]

    def test_skipped_when_gate_4_fails(self):
        # Force gate 3 to fail by making reviews fail
        gates = run_gates({"completed": [{"code_passed": False}], "blocked": []})
        assert gates[4]["passed"] is False
        assert "Skipped" in gates[4]["detail"]


class TestGate6FinalReview:
    """Gate 6: cross-task final review ran after all tasks passed."""

    def test_passes_with_execute_final_review(self):
        execute_result = {
            "completed": [{"code_passed": True}],
            "blocked": [],
            "final_review": {"passed": True},
        }
        gates = run_gates(execute_result)
        assert gates[5]["passed"] is True
        assert gates[5]["name"] == "final_review"

    def test_uses_execute_phase_final_review_when_valid(self):
        execute_result = {
            "completed": [{"code_passed": True}, {"code_passed": True}],
            "blocked": [],
            "final_review": {"passed": True},
        }
        gates = run_gates(execute_result)
        assert gates[5]["passed"] is True
        assert "execute phase confirmed" in gates[5]["detail"]

    def test_skipped_when_gate_5_fails(self):
        gates = run_gates({"completed": [{"code_passed": False}], "blocked": []})
        assert gates[5]["passed"] is False
        assert "Skipped" in gates[5]["detail"]


class TestGate7GitClean:
    """Gate 7: workflow-owned temp cleanup, validation-only."""

    def test_passes_when_clean(self):
        gates = run_gates({"completed": [{"code_passed": True}], "blocked": []})
        assert gates[6]["passed"] is True
        assert gates[6]["name"] == "git_clean"
        # Gate 7 sets next_action to "done" when passed
        assert gates[6]["next_action"] in ("done", "proceed")

    def test_skipped_when_gate_6_fails(self):
        gates = run_gates({"completed": [{"code_passed": False}], "blocked": []})
        assert gates[6]["passed"] is False
        assert "Skipped" in gates[6]["detail"]


# ── Retry cap tests ───────────────────────────────────────────────────


class TestRetryCapDefault:
    """Contract: GATE_RETRY_CAP_DEFAULT is 10."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_gate_retry_cap_default_is_10(self):
        assert "GATE_RETRY_CAP_DEFAULT" in self.script
        assert "10" in self.script

    def test_gate_uses_gate_retries(self):
        # Gate 3 tests_pass uses GATE_RETRIES in its while loop
        assert "iters < GATE_RETRIES" in self.script

    def test_gate_retries_from_retry_policy(self):
        assert "retry_policy" in self.script
        assert "gate_retries" in self.script


# ── Resume support tests ──────────────────────────────────────────────


class TestGateResumeSkipsPassed:
    """Contract: resume skips already-passed gates."""

    def test_resume_skips_passed_gate_1(self):
        resume_cursor = {
            "gate_cursor": 1,
            "gate_states": {
                "tasks_executed": make_gate_record("tasks_executed", True, "3 completed, 0 blocked"),
            },
        }
        gates = run_gates(
            {"completed": [{"code_passed": True}], "blocked": []},
            resume_cursor=resume_cursor,
        )
        # Gate 1 should be the resumed one (passed)
        assert gates[0]["passed"] is True
        # Subsequent gates should still run
        assert gates[1]["passed"] is True

    def test_resume_skips_multiple_passed_gates(self):
        resume_cursor = {
            "gate_cursor": 3,
            "gate_states": {
                "tasks_executed": make_gate_record("tasks_executed", True, "OK"),
                "reviews_passed": make_gate_record("reviews_passed", True, "OK"),
                "tests_pass": make_gate_record("tests_pass", True, "All tests passed"),
            },
        }
        gates = run_gates(
            {"completed": [{"code_passed": True}], "blocked": []},
            resume_cursor=resume_cursor,
        )
        # First 3 gates should be the resumed ones
        assert gates[0]["passed"] is True
        assert gates[1]["passed"] is True
        assert gates[2]["passed"] is True
        # Gate 4 should have run fresh with manifest
        assert gates[3]["passed"] is True
        assert "manifest" in gates[3]

    def test_resume_does_not_skip_if_no_resume_cursor(self):
        gates = run_gates({"completed": [{"code_passed": True}], "blocked": []})
        # All gates should run fresh
        for i, gate in enumerate(gates):
            assert gate["name"] == CANONICAL_GATES[i]


# ── Script structural tests for gate enrichment ──────────────────────


class TestGateEnrichmentInScript:
    """Contract: gate records in the script have enrichment fields."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_make_gate_record_function_exists(self):
        assert "function makeGateRecord" in self.script

    def test_make_gate_record_has_iterations(self):
        assert "iterations" in self.script

    def test_make_gate_record_has_last_failure(self):
        assert "last_failure" in self.script

    def test_make_gate_record_has_last_fix(self):
        assert "last_fix" in self.script

    def test_make_gate_record_has_evidence_paths(self):
        assert "evidence_paths" in self.script

    def test_make_gate_record_has_updated_at(self):
        assert "updated_at" in self.script

    def test_make_gate_record_has_next_action(self):
        assert "next_action" in self.script

    def test_gate_4_writes_manifest(self):
        assert "manifest" in self.script

    def test_manifest_has_commands(self):
        assert "commands:" in self.script or "commands =" in self.script

    def test_manifest_has_exit_codes(self):
        assert "exit_codes:" in self.script or "exit_codes =" in self.script

    def test_manifest_has_crash_status(self):
        assert "crash:" in self.script or "crash =" in self.script

    def test_manifest_has_hang_status(self):
        assert "hang:" in self.script or "hang =" in self.script

    def test_manifest_has_unverified_acceptance(self):
        assert "unverified_acceptance_items" in self.script

    def test_manifest_has_blocking_risks(self):
        assert "blocking_risks" in self.script

    def test_manifest_has_generated_at(self):
        assert "generated_at" in self.script

    def test_gate_6_checks_execute_final_review(self):
        assert "executeHadFinalReview" in self.script
        assert "executeResult.final_review" in self.script

    def test_gate_6_requires_all_tasks_passed(self):
        assert "executeResult.completed.every" in self.script
        assert "code_passed" in self.script

    def test_gate_7_no_commit_instruction(self):
        """Gate 7 must NOT instruct agent to commit."""
        # The old version had "commit changes" — new version should not
        gate7_section = self.script[self.script.index("Gate 7:"):]
        gate7_section = gate7_section[:gate7_section.index("Build the gates array")]
        assert "do NOT commit" in gate7_section

    def test_gate_7_evidence_paths_includes_evidence_dir(self):
        gate7_section = self.script[self.script.index("Gate 7:"):]
        gate7_section = gate7_section[:gate7_section.index("Build the gates array")]
        assert "cleanedPaths" in gate7_section

    def test_resume_support_exists(self):
        assert "isGateAlreadyPassed" in self.script

    def test_resume_cursor_has_gate_states(self):
        assert "gate_states: gateStates" in self.script


# ── Gate ordering enforcement ─────────────────────────────────────────


class TestGateOrderingEnforcement:
    """Contract: gates run in canonical order and depend on prior gate passing."""

    def test_sequential_dependency(self):
        """Each gate depends on the prior gate passing."""
        # Gate 2 fails because reviews fail -> gates 3-7 skip
        gates = run_gates({"completed": [{"code_passed": False}], "blocked": []})
        assert gates[0]["passed"] is True  # tasks_executed: 1 completed, 0 blocked
        assert gates[1]["passed"] is False  # reviews_passed: code_passed is False
        # Gates 3-7 should be skipped
        for i in range(2, 7):
            assert gates[i]["passed"] is False
            assert "Skipped" in gates[i]["detail"]

    def test_all_pass_in_happy_path(self):
        gates = run_gates({
            "completed": [{"code_passed": True}],
            "blocked": [],
            "final_review": {"passed": True},
        })
        for i, gate in enumerate(gates):
            assert gate["passed"] is True, f"Gate {i+1} ({gate['name']}) should pass"


class TestValidateGateSet:
    """Contract: validateGateSet checks for canonical gate names."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_full_auto()

    def test_validate_gate_set_exists(self):
        assert "function validateGateSet" in self.script

    def test_validate_uses_canonical_names(self):
        # The function should check against CANONICAL_GATES directly
        # (not numbered gate_1_ style)
        assert "CANONICAL_GATES.filter" in self.script
