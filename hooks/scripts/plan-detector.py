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
    r"\barchitecture\s+plan\b|\broadmap\b|\borchestrat(?:e|ion)\s+plan\b|"
    r"\b(?:build|create|make)\b.{0,80}\b(?:site|app|platform|system|dashboard|design system|multi[- ]page)\b|"
    r"(?:做一个|帮我做|使用.{0,20}框架).{0,80}(官网|网站|应用|系统|平台|后台|仪表盘|设计系统|多页))",
    re.IGNORECASE,
)

# Keep the message tight: trigger only when the user is clearly describing work
# that should start in the workflow pipeline rather than a one-off quick fix.
SYSTEM_APPEND = """
PLUGIN PLAN ROUTING ACTIVE

Primary route: `/plan`.
Do not separately invoke `using-claude-code-flow` (now merged into dev-orchestrator); this hook already performed the routing pass.
Inside `/plan`, enforce the plan command hard stops. For vague requests, ask clarification before any plan or implementation. For broad, high-impact, multi-step, cross-domain, unfamiliar, quality-sensitive, or outcome-oriented requests without exact implementation scope, do not stop at a chat proposal and do not write code: require clarification notes, local research, material external/domain research, `plan-brief.md`, applicable design artifacts, document self-review PASS, then explicit approval before implementation. Frontend/UI/site work is one example: include external/UI research and UI `DESIGN.md` when Gate 6 is checked.
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
