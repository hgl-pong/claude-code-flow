#!/usr/bin/env python
"""UserPromptSubmit hook: detect uli keyword and inject ULI mode signal.

When the user includes "uli" (case-insensitive, whole word) anywhere in their
prompt, this hook appends a system-level notice to Claude's context so the
ultrawork skill (ULI branch) is loaded immediately — before any other action.

ULI = Ultra Loop Iteration: autonomous product iteration loop where a PD agent
proposes requirements each cycle and the dev pipeline executes and validates them.

Claude Code hook input format (stdin, JSON):
{
  "session_id": "...",
  "transcript_path": "...",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "<the user's full message text>"
}

Output (stdout, JSON) to append a system prompt section:
{
  "system_prompt_append": "...",
  "continue": true
}
If no uli keyword is found, exit silently (no output) with code 0.
"""

import json
import re
import sys


# Match "uli" as a whole word only (case-insensitive).
# \buli\b prevents matching "Julian", "utility", "uli-something" still matches.
# Does NOT match "ulw" or "ultrawork" — those are handled by ulw-detector.py.
ULI_PATTERN = re.compile(r'\buli\b', re.IGNORECASE)

SYSTEM_APPEND = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 ULI MODE ACTIVE — ULTRA LOOP ITERATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The user activated ULI (Ultra Loop Iteration) mode. You MUST:

1. Invoke the `ultrawork` skill IMMEDIATELY and follow the ULI branch.
   Use: Skill({ skill: "claude-code-flow:ultrawork" })
   The skill will detect ULI mode from the keyword and follow the ULI pipeline.

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
        # Malformed input — don't interfere
        sys.exit(0)

    prompt = data.get("prompt", "")
    if not prompt:
        sys.exit(0)

    if not ULI_PATTERN.search(prompt):
        # No ULI keyword found — pass through silently
        sys.exit(0)

    # ULI keyword detected — inject the system prompt append
    output = {
        "system_prompt_append": SYSTEM_APPEND.strip(),
        "continue": True
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
