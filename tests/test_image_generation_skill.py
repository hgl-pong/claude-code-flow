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


def test_image_generation_skill_frontmatter_and_routing_contract():
    skill = read("skills/image-generation/SKILL.md")
    meta = frontmatter(skill)

    assert meta["name"] == "image-generation"
    assert "generate" in meta["description"].lower()
    assert "image" in meta["description"].lower()
    assert "artist" in meta["description"].lower()
    assert "artist" in skill.lower()
    assert "CCF_MAX_PARALLEL_AGENTS" in skill
    assert "manifest" in skill.lower()
    assert "BLOCKED" in skill
    assert "cx/gpt-5.5-image" in skill
    assert "NINEROUTER_URL" in skill
    assert "NINEROUTER_KEY" in skill


def test_artist_prompt_status_protocol_and_manifest_contract():
    prompt = read("skills/subagent-driven-development/artist-prompt.md")

    for status in ["DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"]:
        assert status in prompt

    assert "manifest" in prompt.lower()
    assert "output path" in prompt.lower() or "output paths" in prompt.lower()
    assert "cx/gpt-5.5-image" in prompt
    assert "NINEROUTER_URL" in prompt
    assert "NINEROUTER_KEY" in prompt
    assert "rate limit" in prompt.lower()


def test_subagent_driven_development_lists_artist_prompt():
    skill = read("skills/subagent-driven-development/SKILL.md")

    assert "artist-prompt.md" in skill
    assert "image generation" in skill.lower()
    assert "image editing" in skill.lower() or "editing images" in skill.lower()
