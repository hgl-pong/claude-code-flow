#!/bin/bash
# PreToolUse(Bash): warn about unreviewed changes before git commit
TRACK_FILE=".claude/flow/modified-files.txt"
LOG_EVENT_SCRIPT="$(dirname "$0")/log-event.py"

INPUT=$(cat)

if echo "$INPUT" | grep -q '"tool_input"' 2>/dev/null; then
  TOOL_INPUT=$(echo "$INPUT" | sed -n 's/.*"tool_input"[[:space:]]*:[[:space:]]*"\(.*\)"/\1/p' | head -1)
else
  TOOL_INPUT=$(echo "$INPUT" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\(.*\)"/\1/p' | head -1)
fi

# Check if this is a git commit command
if echo "$TOOL_INPUT" | grep -q 'git[[:space:]]\+commit' 2>/dev/null; then
  if [ -f "$TRACK_FILE" ] && [ -s "$TRACK_FILE" ]; then
    COUNT=$(wc -l < "$TRACK_FILE" | tr -d ' ')
    # Log the guard block event
    python "$LOG_EVENT_SCRIPT" tool_guard_block "guard=pre-commit" "file_count=$COUNT" 2>/dev/null || true
    echo '{"decision":"block","reason":"You have '"$COUNT"' unreviewed modified file(s). Consider running /workflow-review first."}' >&2
    exit 2
  fi
fi

exit 0
