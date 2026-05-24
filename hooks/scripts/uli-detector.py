#!/usr/bin/env python
"""UserPromptSubmit hook: detect autonomous ULI keywords and inject ULI mode signal.

When the user includes "uli", "ulw", or "ultrawork" anywhere in their prompt,
this hook appends a system-level notice so the ultrawork skill is loaded
immediately before any other action.
"""

import json
import re
import sys


ULI_PATTERN = re.compile(r'\b(?:uli|ulw)\b|ultrawork', re.IGNORECASE)

SYSTEM_APPEND = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ULI MODE ACTIVE — ULTRA LOOP ITERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The user activated ULI (Ultra Loop Iteration) mode. Legacy ULW/ultrawork prompts now use this same mode. You MUST:

1. Invoke the `ultrawork` skill IMMEDIATELY.
   Use: Skill({ skill: "claude-code-flow:ultrawork" })

2. Do NOT ask for clarification, approval, or confirmation at any point.

3. The loop runs autonomously:
   PD agent proposes requirements → dev pipeline executes →
   hard acceptance validation → if ACCEPT, start next iteration →
   repeat until max_iterations or <uli-done> is emitted.

4. Hard acceptance means ALL of: build passes + tests pass + feature checklist passes.
   Do NOT advance to the next iteration on a partial acceptance.

5. Do NOT stop until max_iterations is reached or the product goal is fully delivered.
   Output <uli-done>SUMMARY</uli-done> ONLY when the loop is complete.

Violating any of these rules breaks ULI mode. The user chose ULI
specifically to get autonomous product iteration. Honour that choice.
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

    if not ULI_PATTERN.search(prompt):
        sys.exit(0)

    output = {
        "system_prompt_append": SYSTEM_APPEND.strip(),
        "continue": True,
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
