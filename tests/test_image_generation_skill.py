from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    lines = text[4:end].splitlines()
    parsed = {}
    for line in lines:
        assert ":" in line
        key, value = line.split(":", 1)
        key = key.strip()
        assert key
        assert key not in parsed
        parsed[key] = value.strip()
    assert set(parsed) == {"name", "description"}
    return parsed


def test_frontmatter_parser_allows_colons_in_values():
    parsed = frontmatter("---\nname: sample\ndescription: Use when input has http://example.test\n---\nBody")

    assert parsed["description"] == "Use when input has http://example.test"


def test_auto_mode_frontmatter_mentions_image_capability():
    skill = read("skills/auto-mode/SKILL.md")
    meta = frontmatter(skill)

    assert meta["name"] == "auto-mode"
    assert "image" in meta["description"].lower()
    assert "image-generation.md" in skill


def test_image_generation_reference_protocol_and_manifest_contract():
    ref = read("skills/auto-mode/references/image-generation.md")

    for status in ["DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"]:
        assert status in ref

    assert "artist" in ref.lower()
    assert "manifest" in ref.lower()
    assert "output path" in ref.lower() or "output paths" in ref.lower()
    assert "cx/gpt-5.5-image" in ref
    assert "generate-image.py" in ref
    assert "NINEROUTER_URL" in ref
    assert "NINEROUTER_KEY" in ref
    assert "rate" in ref.lower()


def test_auto_mode_lists_image_and_2d_game_references():
    skill = read("skills/auto-mode/SKILL.md")
    game_ref = read("skills/auto-mode/references/2d-game-workflow.md")

    assert "image-generation.md" in skill
    assert "2d-game-workflow.md" in skill
    assert "image generation" in skill.lower()
    assert "sprite" in game_ref
    assert "Phaser" in game_ref
