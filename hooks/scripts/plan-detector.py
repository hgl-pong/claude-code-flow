#!/usr/bin/env python
"""UserPromptSubmit hook: detect plugin plan intent and inject one routing hint."""

import json
import re
import sys

PLAN_PATTERN = re.compile(
    r"(?:/plan\b|\bplan\s+mode\b|"
    r"\bneed\s+a\s+plan\b|\bhelp\s+me\s+plan\b|\bplan\s+first\b|"
    r"\bplanning\b|\bplan\s+(?:a|an|the|this)\b|\boutline\b|\bnext\s+steps\b|"
    r"\bmulti[- ]step\s+plan\b|\bcross[- ]?domain\s+plan\b|"
    r"\barchitecture\s+plan\b|\broadmap\b|\borchestrat(?:e|ion)\s+plan\b)",
    re.IGNORECASE,
)

# Keep the message tight: trigger only when the user is clearly describing work
# that should start in the workflow pipeline rather than a one-off quick fix.
SYSTEM_APPEND = """
PLUGIN PLAN ROUTING ACTIVE

Primary route: `/plan`.
Do not separately invoke `using-claude-code-flow`; this hook already performed the routing pass.
Inside `/plan`, use `brainstorming` only if unresolved product/design decisions remain. Skip brainstorming for approved requirements, direct execution, narrow fixes, routine maintenance, or saved specs.
IMPORTANT: Do not enter built-in plan mode.
Use /plan instead, and avoid invoking EnterPlanMode.
"""


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            sys.exit(0)
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    prompt = data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    # Other slash commands own their route. Do not redirect them back into plan.
    if re.match(r"^\s*/(?!plan\b)", prompt):
        sys.exit(0)

    if not PLAN_PATTERN.search(prompt):
        sys.exit(0)

    output = {
        "system_prompt_append": SYSTEM_APPEND.strip(),
        "continue": True,
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
