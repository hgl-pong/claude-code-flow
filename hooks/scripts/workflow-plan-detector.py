#!/usr/bin/env python
"""UserPromptSubmit hook: detect workflow-plan intent and inject a routing hint."""

import json
import re
import sys

WORKFLOW_PLAN_PATTERN = re.compile(
    r"(?:/plan\b|\bworkflow[- ]?plan\b|\bwrite[- ]?plan\b|\bexecute[- ]?plan\b|\bplan\s+mode\b|\bneed\s+a\s+plan\b|\bhelp\s+me\s+plan\b|\bplan\s+first\b|\boutline\b|\bnext\s+steps\b|\bmulti[- ]step\b|\bcross[- ]?domain\b|\barchitecture\b|\brefactor\b|\broadmap\b|\borchestrate\b)",
    re.IGNORECASE,
)

# Keep the message tight: trigger only when the user is clearly describing work that
# should start in the workflow pipeline rather than a one-off quick fix.

SYSTEM_APPEND = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKFLOW PLAN ROUTING ACTIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The user intent looks like multi-step planning or orchestration.
Before acting, invoke `using-claude-code-flow`, then route to `workflow-plan`.
Prefer `brainstorming` first when the task changes behavior, UI, architecture, or spans multiple files.
IMPORTANT: Do not enter built-in plan mode.
Use /plan or workflow-plan instead, and avoid invoking EnterPlanMode.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

    if not WORKFLOW_PLAN_PATTERN.search(prompt):
        sys.exit(0)

    output = {
        "system_prompt_append": SYSTEM_APPEND.strip(),
        "continue": True,
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
