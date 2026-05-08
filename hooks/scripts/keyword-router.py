#!/usr/bin/env python3
"""Keyword-based skill router for UserPromptSubmit hook.

Detects task patterns in user prompts and suggests matching skills
via additionalContext. Complements (doesn't replace) using-claude-code-flow.
"""
import json
import re
import sys
import os

ROUTING_RULES = [
    (r'\b(debug|fix|broken|crash|error|failing|bug)\b', 'systematic-debugging', 'Debug pattern detected'),
    (r'\b(review|code.?quality|refactor|clean.?up)\b', 'code-quality', 'Review pattern detected'),
    (r'\b(test|spec|coverage|unit.?test|integration.?test)\b', 'testing-strategy', 'Testing pattern detected'),
    (r'\b(plan|architect|design|blueprint)\b', 'workflow-plan', 'Planning pattern detected'),
    (r'\b(brainstorm|idea|explore|spike)\b', 'brainstorming', 'Brainstorm pattern detected'),
    (r'\b(verify|acceptance|done|complete|ship)\b', 'verification-before-completion', 'Verification pattern detected'),
    (r'\b(search|research|look.?up|find.?out|docs?)\b', 'web-search', 'Research pattern detected'),
    (r'\b(write|create|implement|build|add)\b.*\b(plan|spec|design)\b', 'writing-plans', 'Plan writing detected'),
]

# Skip routing if these are present (already routed by other hooks)
SKIP_PATTERNS = [
    r'^\s*/',  # slash commands already routed
    r'\b(ulw|ultrawork|uli)\b',  # autonomous modes handled by dedicated hooks
]


def route_keywords(prompt_text):
    """Match prompt against routing rules, return skill suggestions."""
    if not prompt_text or not prompt_text.strip():
        return None

    # Skip if already routed
    for pattern in SKIP_PATTERNS:
        if re.search(pattern, prompt_text, re.IGNORECASE):
            return None

    matches = []
    for pattern, skill, reason in ROUTING_RULES:
        if re.search(pattern, prompt_text, re.IGNORECASE):
            matches.append((skill, reason))

    if not matches:
        return None

    # Return first match (highest priority)
    skill, reason = matches[0]
    return f"[keyword-router] {reason}. Consider using skill: {skill}"


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    result = route_keywords(prompt)

    if result:
        output = {
            "hookSpecificOutput": {
                "additionalContext": result
            }
        }
        print(json.dumps(output))
    else:
        print("{}")


if __name__ == "__main__":
    main()
