"""Contracts for auto-mode docs and folded dynamic workflow capabilities."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
AUTO_DIR = SKILLS_DIR / "auto-mode"
AUTO_SKILL = AUTO_DIR / "SKILL.md"
AUDIT_TRAIL_REF = AUTO_DIR / "references" / "audit-trail.md"
IMAGE_REF = AUTO_DIR / "references" / "image-generation.md"
GAME_REF = AUTO_DIR / "references" / "2d-game-workflow.md"
ARTIST_PROMPT = AUTO_DIR / "prompts" / "artist-prompt.md"
FULL_AUTO = AUTO_DIR / "workflows" / "full-auto-pipeline.workflow.js"
EXECUTE_PLAN = FULL_AUTO  # consolidated into single file

CANONICAL_GATES = [
    "tasks_executed", "reviews_passed", "tests_pass",
    "runtime_evidence", "spec_verified", "final_review", "git_clean",
]
RESULT_PARTITIONS = ["passed", "completed", "blocked", "stalled", "failed_review", "needs_escalation"]
BLOCKER_TAXONOMY = [
    "agent_output_invalid", "merge_conflict", "permissions", "external_service",
    "tooling_unavailable", "test_failure", "runtime_failure", "dependency_failure",
    "architecture_decision", "scope_too_large", "missing_context",
]
ESCALATION_LADDER = ["schema_retry", "self_service_retry", "stronger_model", "split_subtask", "enriched_context", "ask_user"]
GATE_4_MANIFEST_FIELDS = ["commands", "exit_codes", "logs", "screenshots", "artifacts", "crash", "hang", "unverified_acceptance_items", "blocking_risks", "generated_at"]
TASK_EVIDENCE_FIELDS = ["commit_sha", "test_results", "verification_commands", "evidence_paths", "concerns", "files_modified"]


def _read(path: Path) -> str:
    assert path.exists(), f"File not found: {path}"
    return path.read_text(encoding="utf-8")


class TestDocFilesExist:
    def test_auto_skill_exists(self):
        assert AUTO_SKILL.exists()

    def test_audit_trail_ref_exists(self):
        assert AUDIT_TRAIL_REF.exists()

    def test_folded_refs_exist(self):
        assert IMAGE_REF.exists()
        assert GAME_REF.exists()

    def test_artist_prompt_exists(self):
        assert ARTIST_PROMPT.exists()

    def test_dynamic_workflow_internals_exist(self):
        assert FULL_AUTO.exists()
        assert EXECUTE_PLAN.exists()


class TestGatesInDocs:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.audit_ref = _read(AUDIT_TRAIL_REF)
        self.auto_skill = _read(AUTO_SKILL)
        self.full_auto = _read(FULL_AUTO)

    @pytest.mark.parametrize("gate", CANONICAL_GATES)
    def test_gate_in_audit_trail_ref(self, gate):
        assert gate in self.audit_ref

    @pytest.mark.parametrize("gate", CANONICAL_GATES)
    def test_gate_in_auto_skill(self, gate):
        assert gate in self.auto_skill

    @pytest.mark.parametrize("gate", CANONICAL_GATES)
    def test_gate_in_dynamic_workflow(self, gate):
        assert gate in self.full_auto

    def test_seven_gates_in_auto_skill(self):
        assert sum(1 for g in CANONICAL_GATES if g in self.auto_skill) == 7


class TestResultPartitionsInDocs:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.audit_ref = _read(AUDIT_TRAIL_REF)
        self.exec_plan = _read(EXECUTE_PLAN)

    @pytest.mark.parametrize("partition", RESULT_PARTITIONS)
    def test_partition_in_audit_trail(self, partition):
        assert partition in self.audit_ref

    @pytest.mark.parametrize("partition", RESULT_PARTITIONS)
    def test_partition_in_execute_plan(self, partition):
        assert partition in self.exec_plan


class TestTaxonomyAndEscalationInDocs:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.audit_ref = _read(AUDIT_TRAIL_REF)
        self.full_auto = _read(FULL_AUTO)

    @pytest.mark.parametrize("blocker", BLOCKER_TAXONOMY)
    def test_blocker_in_audit_trail(self, blocker):
        assert blocker in self.audit_ref

    @pytest.mark.parametrize("stage", ESCALATION_LADDER)
    def test_stage_in_audit_trail(self, stage):
        assert stage in self.audit_ref

    @pytest.mark.parametrize("stage", ESCALATION_LADDER)
    def test_stage_in_dynamic_workflow(self, stage):
        assert stage in self.full_auto


class TestEvidenceManifestInDocs:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)
        self.audit_ref = _read(AUDIT_TRAIL_REF)

    @pytest.mark.parametrize("field", GATE_4_MANIFEST_FIELDS)
    def test_manifest_field_in_auto_and_audit(self, field):
        assert field in self.auto_skill
        assert field in self.audit_ref

    @pytest.mark.parametrize("field", TASK_EVIDENCE_FIELDS)
    def test_task_evidence_field_in_audit_trail(self, field):
        assert field in self.audit_ref


class TestResumeAndAuditDocs:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)
        self.audit_ref = _read(AUDIT_TRAIL_REF)

    @pytest.mark.parametrize("text", ["resume_cursor", "gate_cursor", "result_replay", "state.json", "flow-state.py", "event", "update", "revision", "One Active Run"])
    def test_minimal_resume_contract(self, text):
        assert text in self.auto_skill or text in self.audit_ref


class TestAutoModeFinalizationInDocs:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)

    @pytest.mark.parametrize("text", [
        "do not ask", "all seven completion gates pass", "proceed directly to final delivery",
        "No post-pass approval prompt", "Branch completion", "Final Summary",
        "state_file", "audit_events", "evidence_dir", "resume_cursor", "harness-owned",
    ])
    def test_auto_mode_finalizes_without_extra_user_prompt(self, text):
        assert text in self.auto_skill or text.lower() in self.auto_skill.lower()


class TestFoldedCapabilities:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.auto_skill = _read(AUTO_SKILL)
        self.image_ref = _read(IMAGE_REF)
        self.game_ref = _read(GAME_REF)
        self.artist_prompt = _read(ARTIST_PROMPT)

    @pytest.mark.parametrize("text", ["image-generation.md", "2d-game-workflow.md", "image generation", "sprite"])
    def test_auto_mode_links_folded_capabilities(self, text):
        assert text in self.auto_skill

    @pytest.mark.parametrize("text", ["cx/gpt-5.5-image", "generate-image.py", "NINEROUTER_URL", "NINEROUTER_KEY", "BLOCKED", "manifest", "artist-prompt.md"])
    def test_image_generation_contract(self, text):
        assert text in self.image_ref

    @pytest.mark.parametrize("text", ["scripts/generate-image.py", "output_paths", "manifest", "NEEDS_CONTEXT", "Never describe missing files as generated"])
    def test_artist_prompt_contract(self, text):
        assert text in self.artist_prompt

    @pytest.mark.parametrize("text", ["Phaser", "simulation", "renderer", "DOM", "asset", "image-generation.md", "playtest"])
    def test_2d_game_guidance(self, text):
        assert text in self.game_ref


class TestReviewPromptContracts:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.spec_prompt = _read(AUTO_DIR / "prompts" / "spec-reviewer-prompt.md")
        self.code_prompt = _read(AUTO_DIR / "prompts" / "code-quality-reviewer-prompt.md")

    @pytest.mark.parametrize("text", [
        "Diff-First Review Rules", "requirements/acceptance only", "actual code diff",
        "unverified_acceptance_refs", "location_unavailable_reason", "prior_issue_id",
        "Free-form severity/category/location values",
    ])
    def test_spec_review_prompt_is_diff_first(self, text):
        assert text in self.spec_prompt

    @pytest.mark.parametrize("text", [
        "Review the verified controller diff", "controller diff metadata first",
        "files_modified", "diff_verified=false", "conflicting scope",
        "location_unavailable_reason", "prior_issue_id",
        "Free-form severity/category/location values",
    ])
    def test_code_review_prompt_is_diff_first(self, text):
        assert text in self.code_prompt


class TestPromptContractMirrors:
    @pytest.fixture(autouse=True)
    def _load(self):
        prompts = AUTO_DIR / "prompts"
        self.researcher = _read(prompts / "researcher-prompt.md")
        self.planner = _read(prompts / "oracle-planner-prompt.md")
        self.implementer = _read(prompts / "implementer-prompt.md")
        self.forge = _read(prompts / "forge-implementer-prompt.md")
        self.spec_prompt = _read(prompts / "spec-reviewer-prompt.md")
        self.code_prompt = _read(prompts / "code-quality-reviewer-prompt.md")
        self.prism = _read(prompts / "prism-verifier-prompt.md")

    @pytest.mark.parametrize("prompt_name", ["researcher", "planner", "implementer", "forge", "spec_prompt", "code_prompt", "prism"])
    @pytest.mark.parametrize("legacy", ["Task tool", "Task tool (general-purpose)", "general-purpose agent", "paste it here", "paste the report"])
    def test_full_auto_prompt_mirrors_drop_dispatch_residue(self, prompt_name, legacy):
        assert legacy not in getattr(self, prompt_name)

    def test_researcher_matches_research_schema(self):
        for text in ["RESEARCH_SCHEMA", "angle", "findings", "Markdown string", "key_insights", "open_questions"]:
            assert text in self.researcher
        assert ".claude/research" not in self.researcher

    @pytest.mark.parametrize("text", [
        "PLAN_SCHEMA", "TASKS_SCHEMA", "TASK_ITEM_SCHEMA", "ID: task-N", "Depends on:",
        "Acceptance refs:", "Runtime evidence required:", "depends_on", "acceptance_refs",
        "runtime_evidence_required", "risk", "subsystem",
    ])
    def test_planner_matches_parser_metadata(self, text):
        assert text in self.planner

    @pytest.mark.parametrize("prompt_name", ["implementer", "forge"])
    def test_implementer_prompts_match_implement_result(self, prompt_name):
        prompt = getattr(self, prompt_name)
        assert "NEEDS_CONTEXT" not in prompt
        for text in [
            "IMPLEMENT_RESULT", "DONE", "DONE_WITH_CONCERNS", "BLOCKED",
            "test_results", "verification_commands", "verification_results", "base_sha", "head_sha",
            "acceptance_coverage", "unverified_acceptance_refs", "concerns", "diff_summary",
            "concerns: []", "blocker_detail",
        ]:
            assert text in prompt

    @pytest.mark.parametrize("prompt_name", ["implementer", "forge"])
    @pytest.mark.parametrize("text", [
        "FIX_RESULT", "fixed_issue_ids", "targeted_verification", "verification_failures",
        "unrelated_files_changed", "scope_justifications",
    ])
    def test_fix_result_addendum_fields(self, prompt_name, text):
        assert text in getattr(self, prompt_name)

    @pytest.mark.parametrize("prompt_name", ["spec_prompt", "code_prompt"])
    @pytest.mark.parametrize("text", [
        "REVIEW_RESULT", "REVIEW_REREVIEW_RESULT", "prior_findings_verified",
        "unresolved_issue_ids", "new_issues", "diff_verified", "targeted_verification_credible",
        "scope_concerns", "passed: true", "blocking",
    ])
    def test_review_prompts_match_rereview_contract(self, prompt_name, text):
        assert text in getattr(self, prompt_name)

    @pytest.mark.parametrize("text", ["GATE_RESULT", "commands", "exit_codes", "logs", "screenshots", "artifacts", "crash", "hang", "unverified_acceptance_items", "blocking_risks", "generated_at", "evidence_dir"])
    def test_prism_is_gate_evidence_companion(self, text):
        assert text in self.prism


class TestDesignOptionalContracts:
    @pytest.fixture(autouse=True)
    def _load(self):
        prompts = AUTO_DIR / "prompts"
        self.designer = _read(prompts / "designer-prompt.md")
        self.format = _read(prompts / "design-md-format.md")
        self.reviewer = _read(prompts / "design-reviewer-prompt.md")
        self.full_auto = _read(FULL_AUTO)

    @pytest.mark.parametrize("text", [
        ".claude/auto/<task>/design/ui-research.md",
        "root `DESIGN.md`",
        ".claude/auto/<task>/design/design-review.md",
        "controller-provided", "optional UI/UX companion", "codebase constraints",
        "UX framing", "visual hierarchy", "responsive behavior", "keyboard/focus",
        "Cross-reference table", "package installs", "new dependencies",
        "broad style-system rewrites", "extra root artifacts",
    ])
    def test_designer_uses_controller_paths_and_strong_design_contract(self, text):
        assert text in self.designer

    @pytest.mark.parametrize("text", [
        "project root", "DESIGN.md",
        "loading, empty, error", "edge states", "Decision Traceability",
    ])
    def test_design_format_is_controller_path_ready(self, text):
        assert text in self.format

    @pytest.mark.parametrize("text", [
        "root `DESIGN.md`", ".claude/auto/<task>/design/ui-research.md",
        "new dependencies", "extra root artifacts", "non-UI mandatory design",
        "codebase constraints", "responsive behavior", "visual hierarchy",
    ])
    def test_design_reviewer_blocks_scope_drift(self, text):
        assert text in self.reviewer

    @pytest.mark.parametrize("text", [
        "DESIGN_CLASSIFICATION_SCHEMA", "design_applicable", "Non-UI task:",
        "design-classifier", "write-design", "review-design", "fix-design-r",
        "ui-research.md", "DESIGN.md", "design-review.md",
    ])
    def test_full_auto_has_conditional_design_stage_contract(self, text):
        assert text in self.full_auto


class TestAuditEventTypesInDocs:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.audit_ref = _read(AUDIT_TRAIL_REF)

    @pytest.mark.parametrize("event", ["phase_start", "run_complete", "stopped_ask_user", "gate_result", "task_result", "escalation", "review_result"])
    def test_event_type(self, event):
        assert event in self.audit_ref


class TestGameWorkflowPromptContracts:
    @pytest.fixture(autouse=True)
    def _load(self):
        prompts = AUTO_DIR / "prompts"
        self.game_ref = _read(GAME_REF)
        self.planner = _read(prompts / "oracle-planner-prompt.md")
        self.implementer = _read(prompts / "implementer-prompt.md")
        self.artist = _read(prompts / "artist-prompt.md")
        self.prism = _read(prompts / "prism-verifier-prompt.md")
        self.skill = _read(AUTO_SKILL)
        self.full_auto = _read(FULL_AUTO)

    @pytest.mark.parametrize("text", [
        "prompt-only Phaser + TypeScript + Vite",
        "React/canvas",
        "plain TypeScript canvas",
        "Three.js",
        "named non-browser runtimes",
        "Detection precedence",
        "semantic actions",
        "Preview before wiring",
        "unverified_acceptance_items",
        "blocking_risks",
        "Runtime evidence:",
    ])
    def test_2d_game_reference_covers_runtime_and_evidence(self, text):
        assert text in self.game_ref

    @pytest.mark.parametrize("text", [
        "data-contract",
        "asset-manifest",
        "Runtime evidence required: required",
        "screenshots/logs/artifacts",
        "unverified refs/risks",
    ])
    def test_planner_game_metadata_contract(self, text):
        assert text in self.planner

    @pytest.mark.parametrize("text", [
        "2d-game-workflow.md",
        "verify output files exist",
        "previewable artifact",
        "semantic actions",
        "smoke/playtest evidence",
    ])
    def test_implementer_game_asset_and_runtime_contract(self, text):
        assert text in self.implementer or text in self.full_auto

    @pytest.mark.parametrize("text", [
        "sprite sheet",
        "frame_width",
        "frame_height",
        "frame_count",
        "collision bounds",
        "preview evidence",
    ])
    def test_artist_game_manifest_contract(self, text):
        assert text in self.artist

    @pytest.mark.parametrize("text", [
        "render surface/canvas",
        "semantic inputs",
        "core-loop observation",
        "conditional failure/restart",
        "conditional asset load",
        "Generic build logs alone must not clean-pass",
    ])
    def test_verifier_browser_game_runtime_contract(self, text):
        assert text in self.prism or text in self.full_auto

    def test_final_summary_runtime_evidence_line(self):
        assert "Runtime evidence: <commands>; <playtest observation>; artifacts: <screenshots/logs/artifacts or none>; unverified: <refs or none>" in self.skill

    def test_design_classifier_splits_game_visual_from_simulation(self):
        assert "2D browser game playable canvas/HUD/menu/control" in self.full_auto
        assert "pure game simulation/rules/data/docs/config/internal work" in self.full_auto
        assert "Mixed game requests should split" in self.full_auto
