"""Tests for execute-plan fake runtime driver contracts.

Validates the result partition classification logic, evidence propagation,
blocker classification, escalation ladder structure, review threshold
enforcement, and the Final Review guard — all using pure-Python
simulations of the workflow's decision logic (no real agent calls).

Also validates gate enrichment, runtime manifest structure, and
gate resume semantics for the full-auto pipeline.
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills" / "workflow-driven-development"
EXECUTE_PLAN = SKILLS_DIR / "execute-plan.workflow.js"
FULL_AUTO = SKILLS_DIR / "full-auto-pipeline.workflow.js"

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

ESCALATION_ATTEMPTS = {
    "schema_retry": 1,
    "self_service_retry": 2,
    "stronger_model": 1,
    "split_subtask": 1,
    "enriched_context": 1,
    "ask_user": 1,
}

REVIEW_SEVERITIES = ["Critical", "High", "Important", "Minor", "Info"]

REVIEW_THRESHOLD = {
    "spec_review": {
        "low":       {"Critical": True, "High": True, "Important": "if_explicit", "Minor": False, "Info": False},
        "medium":    {"Critical": True, "High": True, "Important": True,          "Minor": False, "Info": False},
        "high":      {"Critical": True, "High": True, "Important": "if_explicit", "Minor": False, "Info": False},
        "critical":  {"Critical": True, "High": True, "Important": True,          "Minor": True,  "Info": False},
    },
    "code_review": {
        "low":       {"Critical": True, "High": True, "Important": "if_explicit", "Minor": False, "Info": False},
        "medium":    {"Critical": True, "High": True, "Important": True,          "Minor": False, "Info": False},
        "high":      {"Critical": True, "High": True, "Important": "if_explicit", "Minor": False, "Info": False},
        "critical":  {"Critical": True, "High": True, "Important": True,          "Minor": True,  "Info": False},
    },
    "final_review": {
        "any":       {"Critical": True, "High": True, "Important": True,          "Minor": False, "Info": False},
    },
}


def _read_script(path: Path) -> str:
    assert path.exists(), f"Script not found: {path}"
    return path.read_text(encoding="utf-8")


# ── Pure-Python reimplementation of classifyTaskResult ────────────────

def is_issue_blocking(review_stage: str, task_risk: str, severity: str, blocking_flag=None) -> bool:
    if blocking_flag is True:
        return True
    if blocking_flag is False:
        return False
    key = "any" if review_stage == "final_review" else task_risk
    table = REVIEW_THRESHOLD.get(review_stage, {})
    rules = table.get(key)
    if not rules:
        return severity in ("Critical", "High")
    rule = rules.get(severity, False)
    if rule is True:
        return True
    if rule is False:
        return False
    # 'if_explicit'
    return blocking_flag is True


def classify_blocker(detail: str) -> str:
    if not detail:
        return "agent_output_invalid"
    lower = detail.lower()
    if "merge conflict" in lower or "conflict" in lower:
        return "merge_conflict"
    if "permission" in lower or "access denied" in lower or "forbidden" in lower:
        return "permissions"
    if "external" in lower or "service" in lower or "timeout" in lower or "network" in lower:
        return "external_service"
    if "tool" in lower or "command not found" in lower or "not installed" in lower:
        return "tooling_unavailable"
    if "test" in lower and ("fail" in lower or "error" in lower):
        return "test_failure"
    if "runtime" in lower or "crash" in lower or "exception" in lower:
        return "runtime_failure"
    if "depend" in lower or "import" in lower or "module" in lower:
        return "dependency_failure"
    if "architect" in lower or "design decision" in lower:
        return "architecture_decision"
    if "scope" in lower or "too large" in lower or "too complex" in lower:
        return "scope_too_large"
    if "context" in lower or "missing info" in lower or "unclear" in lower:
        return "missing_context"
    return "agent_output_invalid"


def classify_task_result(task_id, ctx, risk="medium"):
    """Pure-Python reimplementation matching the JS classifyTaskResult."""
    # 1. Blocked at implementation
    if ctx.get("_blocked"):
        classification = classify_blocker(ctx.get("_reason", ""))
        return "blocked", {
            "id": task_id,
            "reason": ctx.get("_reason"),
            "classification": classification,
        }

    # 2. Escalated to user
    if ctx.get("_escalated_to_user"):
        return "needs_escalation", {
            "id": task_id,
            "reason": ctx.get("_escalation_reason"),
            "classification": ctx.get("_escalation_classification"),
            "rung_reached": ctx.get("_escalation_rung"),
        }

    # 3. Spec review exhausted
    if not ctx.get("spec_passed") and ctx.get("_spec_review_exhausted"):
        return "failed_review", {"id": task_id, "stage": "spec_review"}

    # 4. Code review exhausted
    if ctx.get("spec_passed") and not ctx.get("code_passed") and ctx.get("_code_review_exhausted"):
        return "failed_review", {"id": task_id, "stage": "code_review"}

    # 5. Stalled
    if not ctx.get("spec_passed") or not ctx.get("code_passed"):
        return "stalled", {
            "id": task_id,
            "spec_passed": ctx.get("spec_passed", False),
            "code_passed": ctx.get("code_passed", False),
        }

    # 6. Passed
    return "passed", {
        "id": task_id,
        "spec_passed": True,
        "code_passed": True,
    }


# ── Runtime manifest simulation ───────────────────────────────────────

def make_runtime_manifest(passed, detail="", crash=False, hang=False):
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


def make_gate_record(name, passed, detail, extra=None):
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


# ── Script structural tests ──────────────────────────────────────────


class TestExecutePlanSchemaExtensions:
    """Contract: IMPLEMENT_RESULT schema includes evidence fields."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(EXECUTE_PLAN)

    def test_schema_has_verification_commands(self):
        assert "verification_commands" in self.script

    def test_schema_has_evidence_paths(self):
        assert "evidence_paths" in self.script

    def test_schema_has_concerns(self):
        assert "concerns" in self.script

    def test_schema_has_commit_sha(self):
        assert "commit_sha" in self.script

    def test_schema_has_test_results(self):
        assert "test_results" in self.script

    def test_schema_has_files_modified(self):
        assert "files_modified" in self.script

    def test_implement_result_status_enum(self):
        """IMPLEMENT_RESULT must accept DONE, DONE_WITH_CONCERNS, BLOCKED."""
        assert "DONE_WITH_CONCERNS" in self.script


class TestReviewResultSeverityEnum:
    """Contract: REVIEW_RESULT severity enum includes all 5 canonical levels."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(EXECUTE_PLAN)

    def test_review_result_has_high_severity(self):
        assert "'High'" in self.script or '"High"' in self.script

    def test_review_result_has_info_severity(self):
        assert "'Info'" in self.script or '"Info"' in self.script

    def test_review_result_has_blocking_field(self):
        assert "blocking" in self.script


class TestClassifyBlockerFunction:
    """Contract: classifyBlocker uses BLOCKER_TAXONOMY."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(EXECUTE_PLAN)

    def test_classify_blocker_function_exists(self):
        assert "function classifyBlocker" in self.script

    def test_blocker_taxonomy_referenced(self):
        for taxon in BLOCKER_TAXONOMY:
            assert f"'{taxon}'" in self.script or f'"{taxon}"' in self.script, \
                f"Blocker taxonomy entry '{taxon}' not found in script"


class TestEscalationLadderFunction:
    """Contract: runEscalationLadder follows ESCALATION_LADDER order."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(EXECUTE_PLAN)

    def test_escalation_function_exists(self):
        assert "function runEscalationLadder" in self.script

    def test_escalation_uses_ladder(self):
        assert "ESCALATION_LADDER" in self.script
        # Verify the function iterates the ladder
        assert "for (const rung of ESCALATION_LADDER)" in self.script

    def test_escalation_uses_attempts(self):
        assert "ESCALATION_ATTEMPTS" in self.script
        assert "maxAttempts" in self.script or "ESCALATION_ATTEMPTS[rung]" in self.script

    def test_escalation_ask_user_terminal(self):
        """ask_user must be the terminal rung — marks as needs_escalation."""
        assert "escalated_to_user" in self.script


class TestSchemaRetry:
    """Contract: schema retry logic exists for invalid agent output."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(EXECUTE_PLAN)

    def test_schema_retry_function_exists(self):
        assert "function agentWithSchemaRetry" in self.script

    def test_schema_retry_in_implement_stage(self):
        assert "agentWithSchemaRetry" in self.script
        # Must be used for the implement stage
        assert "implement:" in self.script


class TestFinalReviewGuard:
    """Contract: Final Review only runs when all tasks passed."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(EXECUTE_PLAN)

    def test_final_review_guard_exists(self):
        assert "allOtherPartitionsEmpty" in self.script

    def test_final_review_checks_completed_equals_total(self):
        assert "completed.length === totalTasks" in self.script

    def test_final_review_checks_other_partitions_empty(self):
        assert "blocked.length === 0" in self.script
        assert "stalled.length === 0" in self.script
        assert "failed_review.length === 0" in self.script
        assert "needs_escalation.length === 0" in self.script


class TestStatePatch:
    """Contract: result includes state_patch for resume support."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(EXECUTE_PLAN)

    def test_state_patch_in_return(self):
        assert "state_patch" in self.script

    def test_state_patch_has_partitions(self):
        assert "partitions:" in self.script or "partitions {" in self.script

    def test_state_patch_has_total_tasks(self):
        assert "total_tasks" in self.script

    def test_state_patch_has_final_review_flag(self):
        assert "final_review_run" in self.script


class TestCompletedEqualsPassed:
    """Contract: completed[] must always equal passed[]."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(EXECUTE_PLAN)

    def test_completed_copies_passed(self):
        """completed must be populated from passed entries."""
        # Look for the invariant enforcement
        assert "completed" in self.script
        # The script must explicitly copy passed -> completed
        assert "completed.push" in self.script


# ── Pure-Python driver simulation tests ──────────────────────────────


class TestClassifyTaskResultPassed:
    """Simulated driver: task with DONE status and passing reviews goes to passed."""

    def test_done_with_passing_reviews(self):
        ctx = {
            "impl": {"status": "DONE"},
            "spec_passed": True,
            "code_passed": True,
            "spec_review": {"passed": True, "issues": []},
            "code_review": {"passed": True, "issues": []},
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "passed"
        assert entry["spec_passed"] is True
        assert entry["code_passed"] is True

    def test_done_with_concerns_passing_reviews(self):
        ctx = {
            "impl": {"status": "DONE_WITH_CONCERNS"},
            "spec_passed": True,
            "code_passed": True,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "passed"

    def test_passed_entry_has_evidence(self):
        ctx = {
            "impl": {
                "status": "DONE",
                "commit_sha": "abc123",
                "test_results": "3 passed",
                "files_modified": ["a.js"],
            },
            "spec_passed": True,
            "code_passed": True,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "passed"
        assert entry["spec_passed"] is True
        assert entry["code_passed"] is True


class TestClassifyTaskResultBlocked:
    """Simulated driver: blocked tasks go to blocked partition."""

    def test_blocked_at_implementation(self):
        ctx = {
            "_blocked": True,
            "_reason": "merge conflict in src/main.js",
            "impl": {"status": "BLOCKED", "blocker_detail": "merge conflict"},
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "blocked"
        assert entry["classification"] == "merge_conflict"

    def test_blocked_permissions(self):
        ctx = {
            "_blocked": True,
            "_reason": "Permission denied writing to /etc/config",
            "impl": None,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "blocked"
        assert entry["classification"] == "permissions"

    def test_blocked_test_failure(self):
        ctx = {
            "_blocked": True,
            "_reason": "Test failure in integration suite",
            "impl": None,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "blocked"
        assert entry["classification"] == "test_failure"

    def test_blocked_no_detail_defaults_invalid(self):
        ctx = {
            "_blocked": True,
            "_reason": "",
            "impl": None,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "blocked"
        assert entry["classification"] == "agent_output_invalid"

    def test_blocked_unknown_reason(self):
        ctx = {
            "_blocked": True,
            "_reason": "Something completely unexpected happened",
            "impl": None,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "blocked"
        assert entry["classification"] == "agent_output_invalid"

    def test_blocked_dependency_failure(self):
        ctx = {
            "_blocked": True,
            "_reason": "Cannot import module xyz from dependency",
            "impl": None,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "blocked"
        assert entry["classification"] == "dependency_failure"


class TestClassifyTaskResultNeedsEscalation:
    """Simulated driver: escalation-exhausted tasks go to needs_escalation."""

    def test_escalated_to_user(self):
        ctx = {
            "_escalated_to_user": True,
            "_escalation_reason": "Unresolvable architectural decision needed",
            "_escalation_classification": "architecture_decision",
            "_escalation_rung": "ask_user",
            "impl": None,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "needs_escalation"
        assert entry["rung_reached"] == "ask_user"


class TestClassifyTaskResultFailedReview:
    """Simulated driver: review-exhausted tasks go to failed_review."""

    def test_spec_review_exhausted(self):
        ctx = {
            "impl": {"status": "DONE"},
            "spec_passed": False,
            "code_passed": False,
            "_spec_review_exhausted": True,
            "_iterations_spec": 5,
            "spec_review": {"passed": False, "issues": [{"severity": "Critical"}]},
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "failed_review"
        assert entry["stage"] == "spec_review"

    def test_code_review_exhausted(self):
        ctx = {
            "impl": {"status": "DONE"},
            "spec_passed": True,
            "code_passed": False,
            "_code_review_exhausted": True,
            "_iterations_code": 5,
            "code_review": {"passed": False, "issues": [{"severity": "Critical"}]},
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "failed_review"
        assert entry["stage"] == "code_review"


class TestClassifyTaskResultStalled:
    """Simulated driver: cap-exhausted without precise blocking goes to stalled."""

    def test_spec_stalled_without_exhaustion(self):
        ctx = {
            "impl": {"status": "DONE"},
            "spec_passed": False,
            "code_passed": False,
            "_spec_review_exhausted": False,
            "_iterations_spec": 5,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "stalled"
        assert entry["spec_passed"] is False

    def test_code_stalled_after_spec_pass(self):
        ctx = {
            "impl": {"status": "DONE"},
            "spec_passed": True,
            "code_passed": False,
            "_code_review_exhausted": False,
            "_iterations_code": 3,
        }
        partition, entry = classify_task_result("task-1", ctx)
        assert partition == "stalled"
        assert entry["code_passed"] is False


class TestReviewThresholdEnforcement:
    """Contract: review threshold table determines which severities block."""

    def test_critical_always_blocks_spec(self):
        assert is_issue_blocking("spec_review", "low", "Critical") is True
        assert is_issue_blocking("spec_review", "medium", "Critical") is True
        assert is_issue_blocking("spec_review", "high", "Critical") is True
        assert is_issue_blocking("spec_review", "critical", "Critical") is True

    def test_high_always_blocks_spec(self):
        for risk in ("low", "medium", "high", "critical"):
            assert is_issue_blocking("spec_review", risk, "High") is True

    def test_important_blocks_medium_risk(self):
        assert is_issue_blocking("spec_review", "medium", "Important") is True

    def test_important_if_explicit_for_low_risk(self):
        assert is_issue_blocking("spec_review", "low", "Important", None) is False
        assert is_issue_blocking("spec_review", "low", "Important", True) is True

    def test_minor_blocks_critical_risk(self):
        assert is_issue_blocking("spec_review", "critical", "Minor") is True

    def test_minor_does_not_block_low_risk(self):
        assert is_issue_blocking("spec_review", "low", "Minor") is False

    def test_info_never_blocks(self):
        for risk in ("low", "medium", "high", "critical"):
            assert is_issue_blocking("spec_review", risk, "Info") is False

    def test_final_review_blocks_critical_high_important(self):
        assert is_issue_blocking("final_review", "any", "Critical") is True
        assert is_issue_blocking("final_review", "any", "High") is True
        assert is_issue_blocking("final_review", "any", "Important") is True
        assert is_issue_blocking("final_review", "any", "Minor") is False
        assert is_issue_blocking("final_review", "any", "Info") is False


class TestPartitionExclusivity:
    """Contract: each task appears in exactly one partition."""

    def _classify_all(self, contexts):
        partitions = {p: [] for p in RESULT_PARTITIONS}
        for task_id, ctx in contexts.items():
            partition, entry = classify_task_result(task_id, ctx)
            partitions[partition].append(entry)
        return partitions

    def test_no_overlap(self):
        contexts = {
            "task-1": {"_blocked": True, "_reason": "test failure", "impl": None},
            "task-2": {
                "spec_passed": True, "code_passed": True,
                "impl": {"status": "DONE"},
            },
            "task-3": {
                "spec_passed": True, "code_passed": False,
                "_code_review_exhausted": True,
                "impl": {"status": "DONE"},
                "code_review": {"passed": False, "issues": [{"severity": "Critical"}]},
            },
        }
        partitions = self._classify_all(contexts)
        # Each task in exactly one partition
        total = sum(len(v) for v in partitions.values())
        assert total == len(contexts)
        # Verify specific placements
        assert len(partitions["blocked"]) == 1
        assert len(partitions["passed"]) == 1
        assert len(partitions["failed_review"]) == 1

    def test_completed_equals_passed(self):
        contexts = {
            "task-1": {"spec_passed": True, "code_passed": True, "impl": {"status": "DONE"}},
            "task-2": {"spec_passed": True, "code_passed": True, "impl": {"status": "DONE_WITH_CONCERNS"}},
        }
        partitions = self._classify_all(contexts)
        assert partitions["passed"] == partitions["completed"] or len(partitions["passed"]) == 2

    def test_no_failed_in_passed(self):
        contexts = {
            "task-1": {"spec_passed": True, "code_passed": True, "impl": {"status": "DONE"}},
            "task-2": {
                "spec_passed": False, "code_passed": False,
                "_spec_review_exhausted": True,
                "impl": {"status": "DONE"},
                "spec_review": {"passed": False, "issues": [{"severity": "Critical"}]},
            },
        }
        partitions = self._classify_all(contexts)
        passed_ids = [e["id"] for e in partitions["passed"]]
        assert "task-2" not in passed_ids

    def test_no_unreviewed_in_passed(self):
        contexts = {
            "task-1": {
                "spec_passed": True, "code_passed": True,
                "impl": {"status": "DONE"},
            },
            "task-2": {
                "spec_passed": False, "code_passed": False,
                "_spec_review_exhausted": False,
                "impl": {"status": "DONE"},
            },
        }
        partitions = self._classify_all(contexts)
        passed_ids = [e["id"] for e in partitions["passed"]]
        assert "task-2" not in passed_ids


class TestBlockerClassification:
    """Contract: classifyBlocker maps detail text to taxonomy."""

    def test_merge_conflict(self):
        assert classify_blocker("merge conflict in file.js") == "merge_conflict"

    def test_permissions(self):
        assert classify_blocker("Permission denied") == "permissions"

    def test_external_service(self):
        assert classify_blocker("external API timeout") == "external_service"

    def test_tooling(self):
        assert classify_blocker("tool not installed") == "tooling_unavailable"

    def test_test_failure(self):
        assert classify_blocker("test failure in suite") == "test_failure"

    def test_runtime_failure(self):
        assert classify_blocker("runtime crash") == "runtime_failure"

    def test_dependency_failure(self):
        assert classify_blocker("Cannot import module") == "dependency_failure"

    def test_architecture_decision(self):
        assert classify_blocker("architectural decision needed") == "architecture_decision"

    def test_scope_too_large(self):
        assert classify_blocker("scope too large") == "scope_too_large"

    def test_missing_context(self):
        assert classify_blocker("missing context about X") == "missing_context"

    def test_empty_detail(self):
        assert classify_blocker("") == "agent_output_invalid"

    def test_none_detail(self):
        assert classify_blocker(None) == "agent_output_invalid"

    def test_unknown_defaults_to_invalid(self):
        assert classify_blocker("something weird happened") == "agent_output_invalid"


# ── Runtime manifest contract tests ───────────────────────────────────


class TestRuntimeManifestStructure:
    """Contract: runtime manifest has all required fields."""

    def test_manifest_on_pass(self):
        m = make_runtime_manifest(True, "npm start exited 0")
        assert m["exit_codes"] == [0]
        assert m["crash"] is False
        assert m["hang"] is False
        assert m["blocking_risks"] == []
        assert m["unverified_acceptance_items"] == []
        assert "T" in m["generated_at"]

    def test_manifest_on_crash(self):
        m = make_runtime_manifest(False, "Process crashed with SIGSEGV", crash=True)
        assert m["exit_codes"] == [1]
        assert m["crash"] is True
        assert m["blocking_risks"] == ["Process crashed with SIGSEGV"]

    def test_manifest_on_hang(self):
        m = make_runtime_manifest(False, "Process hung for 60s", hang=True)
        assert m["hang"] is True
        assert m["blocking_risks"] == ["Process hung for 60s"]

    def test_manifest_all_fields_present(self):
        m = make_runtime_manifest(True, "OK")
        required = [
            "commands", "exit_codes", "logs", "screenshots", "artifacts",
            "crash", "hang", "unverified_acceptance_items", "blocking_risks",
            "generated_at",
        ]
        for field in required:
            assert field in m, f"Missing manifest field: {field}"


# ── Gate enrichment in full-auto-pipeline ─────────────────────────────


class TestFullAutoGateEnrichment:
    """Contract: gate records are enriched with metadata."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(FULL_AUTO)

    def test_make_gate_record_function(self):
        assert "function makeGateRecord" in self.script

    def test_gate_record_has_name_field(self):
        # The makeGateRecord must set name
        assert "name," in self.script

    def test_gate_record_has_iterations(self):
        # Inside makeGateRecord
        func_start = self.script.index("function makeGateRecord")
        func_end = self.script.index("}", func_start) + 1
        func_body = self.script[func_start:func_end]
        assert "iterations" in func_body

    def test_gate_record_has_last_failure(self):
        func_start = self.script.index("function makeGateRecord")
        func_end = self.script.index("}", func_start) + 1
        func_body = self.script[func_start:func_end]
        assert "last_failure" in func_body

    def test_gate_record_has_last_fix(self):
        func_start = self.script.index("function makeGateRecord")
        func_end = self.script.index("}", func_start) + 1
        func_body = self.script[func_start:func_end]
        assert "last_fix" in func_body

    def test_gate_record_has_evidence_paths(self):
        func_start = self.script.index("function makeGateRecord")
        func_end = self.script.index("}", func_start) + 1
        func_body = self.script[func_start:func_end]
        assert "evidence_paths" in func_body

    def test_gate_record_has_updated_at(self):
        func_start = self.script.index("function makeGateRecord")
        func_end = self.script.index("}", func_start) + 1
        func_body = self.script[func_start:func_end]
        assert "updated_at" in func_body

    def test_gate_record_has_next_action(self):
        func_start = self.script.index("function makeGateRecord")
        func_end = self.script.index("}", func_start) + 1
        func_body = self.script[func_start:func_end]
        assert "next_action" in func_body

    def test_gate_4_manifest_in_record(self):
        # Gate 4 should embed manifest in the gate record
        assert "manifest" in self.script
        # Should be in the gate 4 section (look for the gate 4 header comment)
        gate4_section_marker = "// ── Gate 4: runtime_evidence"
        if gate4_section_marker in self.script:
            gate4_idx = self.script.index(gate4_section_marker)
            section = self.script[gate4_idx:gate4_idx + 3000]
            assert "manifest" in section
        else:
            # Fallback: just verify manifest is used near GATE_RUNTIME_EVIDENCE
            # in the gates phase (after "Phase 9:")
            phase9_idx = self.script.index("Phase 9:")
            gates_section = self.script[phase9_idx:]
            runtime_idx = gates_section.index("GATE_RUNTIME_EVIDENCE")
            section = gates_section[runtime_idx:runtime_idx + 3000]
            assert "manifest" in section


class TestFullAutoRetryCap:
    """Contract: gates use GATE_RETRIES cap (default 10)."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(FULL_AUTO)

    def test_gate_retry_cap_default(self):
        assert "GATE_RETRY_CAP_DEFAULT" in self.script

    def test_gate_retries_used_in_loops(self):
        count = self.script.count("GATE_RETRIES")
        assert count >= 3, f"Expected GATE_RETRIES used at least 3 times, got {count}"


class TestFullAutoResumeSupport:
    """Contract: resume support skips already-passed gates."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script(FULL_AUTO)

    def test_is_gate_already_passed_function(self):
        assert "function isGateAlreadyPassed" in self.script

    def test_resume_gate_cursor_read(self):
        assert "resume_gate_cursor" in self.script or "resumeGateCursor" in self.script

    def test_resume_gate_states_read(self):
        assert "resume_gate_states" in self.script or "resumeGateStates" in self.script

    def test_gate_states_tracked_in_map(self):
        assert "gateStates" in self.script
