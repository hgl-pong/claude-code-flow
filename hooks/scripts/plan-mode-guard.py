#!/usr/bin/env python
"""PreToolUse hook: block built-in EnterPlanMode and redirect to workflow-plan."""

import json
import sys

REDIRECT_MESSAGE = {
    "decision": "block",
    "reason": "Use the plugin workflow plan instead of built-in plan mode.",
    "systemMessage": (
        "[Plan Mode Guard] Built-in plan mode is disabled in this plugin workflow. "
        "Use /plan or workflow-plan instead."
    ),
}


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            sys.exit(0)
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    if tool_name != "EnterPlanMode":
        sys.exit(0)

    print(json.dumps(REDIRECT_MESSAGE))
    sys.exit(2)


if __name__ == "__main__":
    main()
