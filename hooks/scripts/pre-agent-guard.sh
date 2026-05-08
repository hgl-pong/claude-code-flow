#!/bin/bash
# PreToolUse(Agent): validate orchestration context before spawning agents
INPUT=$(cat)
FLOW_DIR=".claude/flow"
LOG_EVENT_SCRIPT="$(dirname "$0")/log-event.py"

# Only check sentinel — all other agents can proceed freely
if echo "$INPUT" | grep -q 'sentinel'; then
  if [ ! -f "$FLOW_DIR/modified-files.jsonl" ] || [ ! -s "$FLOW_DIR/modified-files.jsonl" ]; then
    python "$LOG_EVENT_SCRIPT" tool_guard_block "guard=pre-agent" "agent=sentinel" "reason=no_modified_files" 2>/dev/null || true
    echo '{"decision":"block","reason":"No modified files to review. Run implementation first, or use /code-review for specific files."}' >&2
    exit 2
  fi
fi

exit 0
