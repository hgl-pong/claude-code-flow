"""Tests validating that auto-mode and workflow docs match implementation contracts.

Checks that the documented constants, enums, partition names, gate names,
escalation stages, blocker taxonomy, review thresholds, and schemas in the
SKILL.md files and reference docs are consistent with the workflow scripts.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

# Doc paths
WDD_SKILL = SKILLS_DIR / "workflow-driven-development" / "workflow-engine.md"
AUTO_SKILL = SKILLS_DIR / "auto-mode" / "SKILL.md"
STATE_MACHINE_REF = SKILLS_DIR / "auto-mode" / "references" / "state-machine.md"
AUDIT_TRAIL_REF = SKILLS_DIR / "auto-mode" / "references" / "audit-trail.md"

# Script paths
FULL_AUTO = SKILLS_DIR / "workflow-driven-development" / "full-auto-pipeline.workflow.js"
EXECUTE_PLAN = SKILLS_DIR / "workflow-driven-development" / "execute-plan.workflow.js"

# Expected canonical values from implementation
CANONICAL_GATES = [
    "tasks_executed", "reviews_passed", "tests_pass",
    "runtime_evidence", "spec_verified", "final_review", "git_clean",
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

TERMINAL_STATUSES = ["DONE", "STOPPED_ASK_USER", "FAILED_FATAL", "CANCELLED"]
NONTERMINAL_STATUSES = ["ACTIVE", "PAUSED_COMPACTING", "BLOCKED_ESCALATING"]

TASK_STATUSES = [
    "queued", "implementing", "implemented", "spec_reviewing", "code_reviewing",
    "passed", "blocked", "stalled", "failed_review", "failed", "split",
]

TASK_RISKS = ["low", "medium", "high", "critical"]

RUNTIME_EVIDENCE_VALUES = ["required", "optional", "not_needed"]

GATE_4_MANIFEST_FIELDS = [
    "commands", "exit_codes", "logs", "screenshots", "artifacts",
    "crash", "hang", "unverified_acceptance_items", "blocking_risks", "generated_at",
]

TASK_EVIDENCE_FIELDS = [
    "commit_sha", "test_results", "verification_commands",
    "evidence_paths", "concerns", "files_modified",
]


def _read(path: Path) -> str:
    assert path.exists(), f"File not found: {path}"
    return path.read_text(encoding="utf-8")


def _extract_const_array(script: str, name: str) -> list:
    pattern = rf"const\s+{name}\s*=\s*\[([^\]]+)\]"
    m = re.search(pattern, script)
    if not m:
        return []
    return re.findall(r"'([^']+)'", m.group(1)) + re.findall(r'"([^"]+)"', m.group(1))


# ── Doc files exist ────────────────────────────────────────────────────


class TestDocFilesExist:
    """All required doc files must be present."""

    def test_wdd_skill_exists(self):
        assert WDD_SKILL.exists()

    def test_auto_skill_exists(self):
        assert AUTO_SKILL.exists()

    def test_state_machine_ref_exists(self):
        assert STATE_MACHINE_REF.exists()

    def test_audit_trail_ref_exists(self):
        assert AUDIT_TRAIL_REF.exists()


# ── Canonical gates in docs ────────────────────────────────────────────


class TestGatesInDocs:
    """Docs must reference all 7 canonical gates by name."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.state_ref = _read(STATE_MACHINE_REF)
        self.audit_ref = _read(AUDIT_TRAIL_REF)
        self.auto_skill = _read(AUTO_SKILL)
        self.wdd_skill = _read(WDD_SKILL)

    @pytest.mark.parametrize("gate", CANONICAL_GATES)
    def test_gate_in_state_machine_ref(self, gate):
        assert gate in self.state_ref, f"Gate '{gate}' not found in state-machine.md"

    @pytest.mark.parametrize("gate", CANONICAL_GATES)
    def test_gate_in_audit_trail_ref(self, gate):
        assert gate in self.audit_ref, f"Gate '{gate}' not found in audit-trail.md"

    @pytest.mark.parametrize("gate", CANONICAL_GATES)
    def test_gate_in_auto_skill(self, gate):
        assert gate in self.auto_skill, f"Gate '{gate}' not found in auto-mode SKILL.md"

    def test_seven_gates_in_auto_skill(self):
        """Auto-mode SKILL.md must reference all 7 gates."""
        count = sum(1 for g in CANONICAL_GATES if g in self.auto_skill)
        assert count == 7, f"Expected 7 gates in auto-mode SKILL.md, found {count}"

    def test_gate_7_no_commit_in_wdd(self):
        """WDD SKILL.md must document that gate 7 does not commit."""
        assert "does NOT instruct" in self.wdd_skill or "validation-only" in self.wdd_skill


# ── Result partitions in docs ──────────────────────────────────────────


class TestResultPartitionsInDocs:
    """Docs must document all 6 result partitions."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.wdd_skill = _read(WDD_SKILL)

    @pytest.mark.parametrize("partition", RESULT_PARTITIONS)
    def test_partition_in_wdd_skill(self, partition):
        assert f"`results.{partition}[]`" in self.wdd_skill or \
               f"results.{partition}" in self.wdd_skill or \
               f"`{partition}`" in self.wdd_skill, \
            f"Partition '{partition}' not documented in workflow SKILL.md"

    def test_completed_equals_passed_documented(self):
        assert "completed" in self.wdd_skill
        assert "passed" in self.wdd_skill
        assert "alias" in self.wdd_skill or "backward compatibility" in self.wdd_skill


# ── Blocker taxonomy in docs ───────────────────────────────────────────


class TestBlockerTaxonomyInDocs:
    """Docs must document all blocker taxonomy categories."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.wdd_skill = _read(WDD_SKILL)
        self.audit_ref = _read(AUDIT_TRAIL_REF)

    @pytest.mark.parametrize("blocker", BLOCKER_TAXONOMY)
    def test_blocker_in_wdd_skill(self, blocker):
        assert blocker in self.wdd_skill, f"Blocker '{blocker}' not in workflow SKILL.md"

    @pytest.mark.parametrize("blocker", BLOCKER_TAXONOMY)
    def test_blocker_in_audit_trail(self, blocker):
        assert blocker in self.audit_ref, f"Blocker '{blocker}' not in audit-trail.md"


# ── Escalation ladder in docs ──────────────────────────────────────────


class TestEscalationLadderInDocs:
    """Docs must document all escalation ladder stages."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.wdd_skill = _read(WDD_SKILL)
        self.audit_ref = _read(AUDIT_TRAIL_REF)

    @pytest.mark.parametrize("stage", ESCALATION_LADDER)
    def test_stage_in_wdd_skill(self, stage):
        assert stage in self.wdd_skill, f"Escalation stage '{stage}' not in workflow SKILL.md"

    @pytest.mark.parametrize("stage", ESCALATION_LADDER)
    def test_stage_in_audit_trail(self, stage):
        assert stage in self.audit_ref, f"Escalation stage '{stage}' not in audit-trail.md"


# ── Review threshold in docs ───────────────────────────────────────────


class TestReviewThresholdInDocs:
    """Docs must document the review threshold table."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.wdd_skill = _read(WDD_SKILL)

    def test_review_threshold_section(self):
        assert "Review Threshold" in self.wdd_skill or "review threshold" in self.wdd_skill.lower()

    @pytest.mark.parametrize("risk", TASK_RISKS)
    def test_risk_levels_documented(self, risk):
        assert f"`{risk}`" in self.wdd_skill, f"Risk level '{risk}' not documented"

    def test_if_explicit_documented(self):
        assert "if_explicit" in self.wdd_skill

    def test_spec_review_stage_documented(self):
        assert "spec_review" in self.wdd_skill

    def test_code_review_stage_documented(self):
        assert "code_review" in self.wdd_skill

    def test_final_review_stage_documented(self):
        assert "final_review" in self.wdd_skill


# ── Phase enum in docs ─────────────────────────────────────────────────


class TestPhaseEnumInDocs:
    """State machine reference must document all canonical phases."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.state_ref = _read(STATE_MACHINE_REF)

    @pytest.mark.parametrize("phase", PHASE_ORDER)
    def test_phase_in_state_machine_ref(self, phase):
        assert phase in self.state_ref, f"Phase '{phase}' not in state-machine.md"


# ── Status values in docs ──────────────────────────────────────────────


class TestStatusValuesInDocs:
    """State machine reference must document all status values."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.state_ref = _read(STATE_MACHINE_REF)

    @pytest.mark.parametrize("status", TERMINAL_STATUSES)
    def test_terminal_status_documented(self, status):
        assert status in self.state_ref, f"Terminal status '{status}' not in state-machine.md"

    @pytest.mark.parametrize("status", NONTERMINAL_STATUSES)
    def test_nonterminal_status_documented(self, status):
        assert status in self.state_ref, f"Nonterminal status '{status}' not in state-machine.md"


# ── Task statuses in docs ──────────────────────────────────────────────


class TestTaskStatusesInDocs:
    """Docs must document all task statuses."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.state_ref = _read(STATE_MACHINE_REF)
        self.wdd_skill = _read(WDD_SKILL)

    @pytest.mark.parametrize("status", TASK_STATUSES)
    def test_task_status_in_state_machine(self, status):
        assert status in self.state_ref, f"Task status '{status}' not in state-machine.md"

    @pytest.mark.parametrize("status", TASK_STATUSES)
    def test_task_status_in_wdd_skill(self, status):
        assert status in self.wdd_skill, f"Task status '{status}' not in workflow SKILL.md"


# ── Task metadata fields in docs ───────────────────────────────────────


class TestGameWorkflowGuidance:
    """Workflow docs and prompts must cover 2D browser game development."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.wdd_skill = _read(WDD_SKILL)
        self.oracle_prompt = _read(SKILLS_DIR / "workflow-driven-development" / "oracle-planner-prompt.md")
        self.implementer_prompt = _read(SKILLS_DIR / "workflow-driven-development" / "implementer-prompt.md")
        self.spec_reviewer_prompt = _read(SKILLS_DIR / "workflow-driven-development" / "spec-reviewer-prompt.md")
        self.code_reviewer_prompt = _read(SKILLS_DIR / "workflow-driven-development" / "code-quality-reviewer-prompt.md")

    @pytest.mark.parametrize("text", [
        "2d-game-workflow.md",
        "Phaser",
        "simulation",
        "renderer",
        "DOM",
        "sprite",
        "image-generation",
        "playtest",
    ])
    def test_2d_game_guidance_in_workflow_docs(self, text):
        assert text in self.wdd_skill

    @pytest.mark.parametrize("text", [
        "src/game/simulation",
        "src/game/assets/manifest",
        "src/phaser/scenes",
        "src/ui",
        "camera model",
        "input action map",
        "playtest",
        "image-generation",
    ])
    def test_2d_game_reference_exists(self, text):
        ref = _read(SKILLS_DIR / "workflow-driven-development" / "references" / "2d-game-workflow.md")
        assert text in ref

    @pytest.mark.parametrize("text", ["Phaser", "simulation", "renderer", "DOM HUD", "sprite", "image-generation", "playtest", "asset manifest"])
    def test_2d_game_guidance_in_planner_prompt(self, text):
        assert text in self.oracle_prompt

    @pytest.mark.parametrize("text", ["Phaser", "simulation", "renderer", "DOM HUD", "image-generation", "asset manifest", "playtest"])
    def test_2d_game_guidance_in_implementer_prompt(self, text):
        assert text in self.implementer_prompt

    @pytest.mark.parametrize("text", ["Phaser", "simulation", "renderer", "DOM", "asset", "image-generation", "playtest"])
    def test_2d_game_guidance_in_reviewer_prompts(self, text):
        assert text in self.spec_reviewer_prompt
        assert text in self.code_reviewer_prompt


class TestTaskMetadataInDocs:
    """Docs must document all task metadata fields."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.wdd_skill = _read(WDD_SKILL)

    def test_risk_field_documented(self):
        assert "`risk`" in self.wdd_skill or "risk" in self.wdd_skill

    def test_subsystem_field_documented(self):
        assert "`subsystem`" in self.wdd_skill or "subsystem" in self.wdd_skill

    def test_runtime_evidence_required_documented(self):
        assert "runtime_evidence_required" in self.wdd_skill

    @pytest.mark.parametrize("val", RUNTIME_EVIDENCE_VALUES)
    def test_runtime_evidence_enum_in_docs(self, val):
        assert val in self.wdd_skill, f"runtime_evidence_required value '{val}' not documented"

    def test_depends_on_documented(self):
        assert "depends_on" in self.wdd_skill

    def test_files_documented(self):
        assert "`files`" in self.wdd_skill or "files" in self.wdd_skill

    def test_tests_documented(self):
        assert "`tests`" in self.wdd_skill or "tests" in self.wdd_skill

    def test_verification_documented(self):
        assert "verification" in self.wdd_skill

    def test_acceptance_refs_documented(self):
        assert "acceptance_refs" in self.wdd_skill


# ── Evidence manifest in docs ──────────────────────────────────────────


class TestEvidenceManifestInDocs:
    """Docs must document the runtime evidence manifest fields."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.wdd_skill = _read(WDD_SKILL)
        self.audit_ref = _read(AUDIT_TRAIL_REF)

    @pytest.mark.parametrize("field", GATE_4_MANIFEST_FIELDS)
    def test_manifest_field_in_wdd(self, field):
        assert field in self.wdd_skill, f"Manifest field '{field}' not in workflow SKILL.md"

    @pytest.mark.parametrize("field", GATE_4_MANIFEST_FIELDS)
    def test_manifest_field_in_audit_trail(self, field):
        assert field in self.audit_ref, f"Manifest field '{field}' not in audit-trail.md"

    @pytest.mark.parametrize("field", TASK_EVIDENCE_FIELDS)
    def test_task_evidence_field_in_wdd(self, field):
        assert field in self.wdd_skill, f"Task evidence field '{field}' not in workflow SKILL.md"

    @pytest.mark.parametrize("field", TASK_EVIDENCE_FIELDS)
    def test_task_evidence_field_in_audit_trail(self, field):
        assert field in self.audit_ref, f"Task evidence field '{field}' not in audit-trail.md"


# ── Resume cursor in docs ──────────────────────────────────────────────


class TestResumeCursorInDocs:
    """Docs must document resume cursor fields."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)
        self.state_ref = _read(STATE_MACHINE_REF)

    def test_resume_cursor_section_in_auto_skill(self):
        assert "resume_cursor" in self.auto_skill

    def test_gate_cursor_documented(self):
        assert "gate_cursor" in self.auto_skill
        assert "gate_cursor" in self.state_ref

    def test_result_replay_documented(self):
        assert "result_replay" in self.auto_skill

    def test_spec_path_in_cursor(self):
        assert "spec_path" in self.state_ref

    def test_plan_path_in_cursor(self):
        assert "plan_path" in self.state_ref


# ── State writer handoff in docs ───────────────────────────────────────


class TestStateWriterHandoffInDocs:
    """Docs must document the state writer handoff via flow-state.py."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)
        self.state_ref = _read(STATE_MACHINE_REF)

    def test_state_writer_section_in_auto_skill(self):
        assert "flow-state.py" in self.auto_skill or "flowState" in self.auto_skill

    def test_flow_state_cmd_event(self):
        assert "event" in self.auto_skill

    def test_flow_state_cmd_update(self):
        assert "update" in self.auto_skill

    def test_revision_tracking_documented(self):
        assert "revision" in self.auto_skill or "expected_revision" in self.auto_skill


# ── One active run constraint ──────────────────────────────────────────


class TestOneActiveRunInDocs:
    """Docs must document the one-active-run-per-worktree constraint."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)
        self.state_ref = _read(STATE_MACHINE_REF)

    def test_one_active_run_section(self):
        assert "One Active Run" in self.auto_skill

    def test_terminal_statuses_listed(self):
        for status in TERMINAL_STATUSES:
            assert status in self.state_ref, f"Terminal status '{status}' not in state-machine.md"


# ── Commit policy in docs ──────────────────────────────────────────────


class TestCommitPolicyInDocs:
    """Docs must document commit policy and no-automatic-PR."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.wdd_skill = _read(WDD_SKILL)

    def test_commit_policy_section(self):
        assert "Commit Policy" in self.wdd_skill or "commit policy" in self.wdd_skill.lower()

    def test_no_automatic_pr(self):
        assert "No automatic PR" in self.wdd_skill or "no automatic PR" in self.wdd_skill.lower()


# ── Final summary in docs ──────────────────────────────────────────────


class TestAutoModeFinalizationInDocs:
    """Auto-mode must document autonomous final delivery after gates pass."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)

    @pytest.mark.parametrize("text", [
        "Do not ask",
        "all seven completion gates pass",
        "proceed directly to final delivery",
        "Gate 7 validates cleanliness only",
        "No post-pass approval prompt",
    ])
    def test_auto_mode_finalizes_without_extra_user_prompt(self, text):
        assert text in self.auto_skill

    @pytest.mark.parametrize("text", [
        "research → multi-agent brainstorming",
        "multi-agent brainstorming",
        "Semi-Auto Boundary",
        "human approves spec/plan",
        "reviewers replace approval gates",
    ])
    def test_auto_mode_documents_autonomous_and_semi_auto_boundaries(self, text):
        assert text in self.auto_skill


class TestFinalSummaryInDocs:
    """Docs must document the final summary disclosure fields."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)

    def test_final_summary_section(self):
        assert "Final Summary" in self.auto_skill

    def test_state_file_in_summary(self):
        assert "state_file" in self.auto_skill

    def test_audit_events_in_summary(self):
        assert "audit_events" in self.auto_skill

    def test_evidence_dir_in_summary(self):
        assert "evidence_dir" in self.auto_skill

    def test_resume_cursor_in_summary(self):
        assert "resume_cursor" in self.auto_skill


# ── Cross-doc consistency with scripts ─────────────────────────────────


class TestDocScriptConsistency:
    """Constants in docs must match constants in scripts."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.full_auto = _read(FULL_AUTO)
        self.exec_plan = _read(EXECUTE_PLAN)

    def test_gates_match_script(self):
        script_gates = _extract_const_array(self.full_auto, "CANONICAL_GATES")
        assert script_gates == CANONICAL_GATES

    def test_partitions_match_script(self):
        script_partitions = _extract_const_array(self.full_auto, "RESULT_PARTITIONS")
        assert script_partitions == RESULT_PARTITIONS

    def test_escalation_matches_script(self):
        script_ladder = _extract_const_array(self.full_auto, "ESCALATION_LADDER")
        assert script_ladder == ESCALATION_LADDER

    def test_blocker_taxonomy_matches_script(self):
        script_blockers = _extract_const_array(self.full_auto, "BLOCKER_TAXONOMY")
        assert script_blockers == BLOCKER_TAXONOMY

    def test_terminal_statuses_match_script(self):
        script_statuses = _extract_const_array(self.full_auto, "TERMINAL_STATUSES")
        assert script_statuses == TERMINAL_STATUSES

    def test_nonterminal_statuses_match_script(self):
        script_statuses = _extract_const_array(self.full_auto, "NONTERMINAL_STATUSES")
        assert script_statuses == NONTERMINAL_STATUSES

    def test_phase_order_matches_script(self):
        script_phases = _extract_const_array(self.full_auto, "PHASE_ORDER")
        assert script_phases == PHASE_ORDER


# ── Slash command docs ─────────────────────────────────────────────────


class TestSlashCommandDocs:
    """Docs must note that slash parsing is harness-owned."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)

    def test_harness_owned_note(self):
        assert "harness-owned" in self.auto_skill or "harness" in self.auto_skill


# ── Audit trail event types in docs ────────────────────────────────────


class TestAuditEventTypesInDocs:
    """Audit trail reference must document required event types."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.audit_ref = _read(AUDIT_TRAIL_REF)

    def test_phase_start_event(self):
        assert "phase_start" in self.audit_ref

    def test_run_complete_event(self):
        assert "run_complete" in self.audit_ref

    def test_stopped_ask_user_event(self):
        assert "stopped_ask_user" in self.audit_ref

    def test_gate_result_event(self):
        assert "gate_result" in self.audit_ref

    def test_task_result_event(self):
        assert "task_result" in self.audit_ref

    def test_escalation_event(self):
        assert "escalation" in self.audit_ref

    def test_review_result_event(self):
        assert "review_result" in self.audit_ref
