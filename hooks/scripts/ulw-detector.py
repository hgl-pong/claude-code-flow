#!/usr/bin/env python
"""UserPromptSubmit hook: detect ulw/ultrawork keywords and inject ULW mode signal.

When the user includes "ulw" or "ultrawork" (case-insensitive) anywhere in their
prompt, this hook appends a system-level notice to Claude's context so the
ultrawork skill is loaded immediately — before any other action.

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
If no ulw keyword is found, exit silently (no output) with code 0.
"""

import json
import re
import sys


# Match "ulw" as a whole word, or "ultrawork" anywhere (case-insensitive).
# \bulw\b prevents matching "bulwark", "ulw-something" still matches.
ULW_PATTERN = re.compile(r'\bulw\b|ultrawork', re.IGNORECASE)

SYSTEM_APPEND = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ULW MODE ACTIVE — ULTRAWORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The user activated Ultrawork (ULW) mode. You MUST:

1. Invoke the `ultrawork` skill IMMEDIATELY — before any other action.
   Use: Skill({ skill: "claude-code-flow:ultrawork" })

2. Do NOT ask for clarification, approval, or confirmation at any point.

3. Do NOT present options or designs for review.

4. Run the full pipeline autonomously (Intent Gate → Execute → Verify).

5. Do NOT stop until all tasks have fresh verification evidence.

Violating any of these rules breaks ULW mode. The user chose ULW
specifically to avoid back-and-forth. Honour that choice.
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

    if not ULW_PATTERN.search(prompt):
        # No ULW keyword found — pass through silently
        sys.exit(0)

    # ULW keyword detected — inject the system prompt append
    output = {
        "system_prompt_append": SYSTEM_APPEND.strip(),
        "continue": True
    }
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
