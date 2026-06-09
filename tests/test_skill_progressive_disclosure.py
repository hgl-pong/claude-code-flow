"""Contracts for compact skills and progressive disclosure.

These tests keep frequently-loaded SKILL.md files small while ensuring heavy
reference material stays reachable by explicit markdown references.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"

MAX_SKILL_WORDS = 1000

EXPECTED_REFERENCE_LINKS = {
    "systematic-debugging": [
        "root-cause-tracing.md",
        "defense-in-depth.md",
        "condition-based-waiting.md",
    ],
}

LAYER_ONE_MARKERS = [
    "Core",
    "Use",
    "Red Flags",
    "Stop",
    "Gate",
    "Checklist",
    "Process",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def words(text: str) -> int:
    return len([part for part in re.split(r"\s+", text.strip()) if part])


def skill_dirs() -> list[Path]:
    return sorted(path.parent for path in SKILLS.glob("*/SKILL.md"))


def test_all_skill_docs_stay_compact_for_layer_one_loading():
    oversized = []
    for skill_dir in skill_dirs():
        count = words(read(skill_dir / "SKILL.md"))
        if count > MAX_SKILL_WORDS:
            oversized.append(f"{skill_dir.name}: {count}")

    assert not oversized, "SKILL.md files exceed layer-one word budget: " + ", ".join(oversized)


def test_every_skill_keeps_triggerable_frontmatter_and_layer_one_markers():
    for skill_dir in skill_dirs():
        text = read(skill_dir / "SKILL.md")
        assert text.startswith("---\n"), skill_dir.name
        assert "\nname:" in text or text.startswith("---\nname:"), skill_dir.name
        assert "\ndescription:" in text, skill_dir.name
        assert any(marker in text for marker in LAYER_ONE_MARKERS), skill_dir.name


def test_declared_progressive_disclosure_references_exist_and_are_linked():
    for skill_name, refs in EXPECTED_REFERENCE_LINKS.items():
        text = read(SKILLS / skill_name / "SKILL.md")
        for ref in refs:
            assert ref in text, f"{skill_name} does not link {ref}"
            assert (SKILLS / skill_name / ref).exists(), f"{skill_name} missing referenced file {ref}"


def test_local_markdown_references_from_skill_docs_resolve():
    pattern = re.compile(r"`([^`<>]+\.md)`")
    missing = []
    for skill_dir in skill_dirs():
        text = read(skill_dir / "SKILL.md")
        for ref in pattern.findall(text):
            if "/" in ref or "\\" in ref or ref.startswith("."):
                continue
            if ref == "DESIGN.md":
                continue
            if not (skill_dir / ref).exists() and not (skill_dir / "references" / ref).exists():
                missing.append(f"{skill_dir.name}: {ref}")

    assert not missing, "Unresolved local markdown references: " + ", ".join(missing)
