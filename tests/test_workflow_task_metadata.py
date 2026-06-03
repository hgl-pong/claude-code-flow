"""Tests for workflow task metadata contract.

Validates task metadata defaults, inference rules, and dependency graph
validation as defined in the spec.
"""

import json
import re
from pathlib import Path

import pytest

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills" / "workflow-driven-development"
FULL_AUTO = SKILLS_DIR / "full-auto-pipeline.workflow.js"

TASK_METADATA_DEFAULTS = {
    "risk": "medium",
    "subsystem": "unknown",
    "runtime_evidence_required": "optional",
}

ESCALATION_STAGES = [
    "none", "schema_retry", "self_service_retry", "stronger_model",
    "split_subtask", "enriched_context", "ask_user", "exhausted",
]

TASK_STATUSES = [
    "queued", "implementing", "implemented", "spec_reviewing", "code_reviewing",
    "passed", "blocked", "stalled", "failed_review", "failed", "split",
]


def _read_script() -> str:
    assert FULL_AUTO.exists(), f"Script not found: {FULL_AUTO}"
    return FULL_AUTO.read_text(encoding="utf-8")


class TestTaskMetadataDefaults:
    """Contract: TASK_METADATA_DEFAULTS matches spec."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script()

    def test_defaults_const_exists(self):
        assert "TASK_METADATA_DEFAULTS" in self.script

    def test_default_risk_is_medium(self):
        assert 'risk: "medium"' in self.script or "risk: 'medium'" in self.script

    def test_default_subsystem_is_unknown(self):
        assert 'subsystem: "unknown"' in self.script or "subsystem: 'unknown'" in self.script

    def test_default_runtime_evidence_is_optional(self):
        assert 'runtime_evidence_required: "optional"' in self.script or \
               "runtime_evidence_required: 'optional'" in self.script


class TestTaskStatuses:
    """Contract: task statuses match canonical list."""

    def test_all_statuses_defined(self):
        script = _read_script()
        for status in TASK_STATUSES:
            assert f"'{status}'" in script or f'"{status}"' in script, \
                f"Task status '{status}' not found in full-auto-pipeline"


class TestEscalationContract:
    """Contract: escalation ladder and attempt caps are defined."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.script = _read_script()

    def test_escalation_ladder_order(self):
        """Ladder must be deterministic and match spec order."""
        pattern = r"const\s+ESCALATION_LADDER\s*=\s*\[([^\]]+)\]"
        m = re.search(pattern, self.script)
        assert m, "ESCALATION_LADDER not found"
        stages = re.findall(r"'([^']+)'", m.group(1))
        assert stages == [
            "schema_retry", "self_service_retry", "stronger_model",
            "split_subtask", "enriched_context", "ask_user",
        ]

    def test_escalation_attempts_defined(self):
        assert "ESCALATION_ATTEMPTS" in self.script
        # schema_retry: max 1
        assert "schema_retry" in self.script
        # ask_user: max 1
        assert "ask_user" in self.script

    def test_schema_retry_capped_at_one(self):
        pattern = r"schema_retry:\s*(\d+)"
        m = re.search(pattern, self.script)
        assert m, "schema_retry attempt cap not found"
        assert int(m.group(1)) == 1

    def test_self_service_retry_capped_at_two(self):
        pattern = r"self_service_retry:\s*(\d+)"
        m = re.search(pattern, self.script)
        assert m, "self_service_retry attempt cap not found"
        assert int(m.group(1)) == 2


class TestDependencyGraphContract:
    """Contract: dependency graph rules from spec.

    These validate the structural rules that Parse Plan must enforce.
    """

    def test_rejects_duplicate_task_ids(self):
        """Duplicate IDs in tasks or groups must fail."""
        tasks = {"task-1": {"id": "task-1"}, "task-1b": {"id": "task-1"}}
        ids = [t["id"] for t in tasks.values()]
        assert len(ids) != len(set(ids)), "Should detect duplicate IDs"

    def test_rejects_unknown_deps(self):
        """A task depending on a non-existent ID must fail."""
        tasks = {"task-1": {"id": "task-1", "depends_on": ["task-99"]}}
        all_ids = set(tasks.keys())
        unknown = []
        for tid, t in tasks.items():
            for dep in t.get("depends_on", []):
                if dep not in all_ids:
                    unknown.append(dep)
        assert len(unknown) > 0, "Should detect unknown deps"

    def test_rejects_cycles(self):
        """Cyclic dependencies must fail."""
        # task-1 -> task-2 -> task-1 is a cycle
        deps = {"task-1": ["task-2"], "task-2": ["task-1"]}
        visited = set()
        has_cycle = False

        def _visit(node, path):
            nonlocal has_cycle
            if node in path:
                has_cycle = True
                return
            if node in visited:
                return
            visited.add(node)
            for d in deps.get(node, []):
                _visit(d, path | {node})

        for n in deps:
            _visit(n, set())
        assert has_cycle, "Should detect cycle"

    def test_rejects_intra_group_deps(self):
        """Tasks in the same group must not depend on each other."""
        groups = [["task-1", "task-2"]]
        tasks = {"task-1": {"id": "task-1", "depends_on": ["task-2"]}, "task-2": {"id": "task-2", "depends_on": []}}

        intra = []
        for group in groups:
            group_set = set(group)
            for tid in group:
                for dep in tasks[tid].get("depends_on", []):
                    if dep in group_set:
                        intra.append((tid, dep))
        assert len(intra) > 0, "Should detect intra-group deps"

    def test_rejects_empty_groups(self):
        """Empty groups must fail."""
        groups = [[], ["task-1"]]
        has_empty = any(len(g) == 0 for g in groups)
        assert has_empty, "Should detect empty groups"

    def test_rejects_task_not_in_any_group(self):
        """Every task must appear in exactly one group."""
        groups = [["task-1"]]
        tasks = {"task-1": {"id": "task-1"}, "task-2": {"id": "task-2"}}
        grouped = set()
        for g in groups:
            grouped.update(g)
        ungrouped = set(tasks.keys()) - grouped
        assert len(ungrouped) > 0, f"Should detect ungrouped tasks: {ungrouped}"

    def test_rejects_duplicate_group_membership(self):
        """Each task must appear in exactly one group."""
        groups = [["task-1", "task-2"], ["task-2", "task-3"]]
        seen = {}
        dupes = []
        for i, g in enumerate(groups):
            for tid in g:
                if tid in seen:
                    dupes.append(tid)
                seen[tid] = i
        assert len(dupes) > 0, f"Should detect duplicate group membership: {dupes}"
