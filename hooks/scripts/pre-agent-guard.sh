#!/bin/bash
# PreToolUse(Agent): validate orchestration context before spawning agents
INPUT=$(cat)
FLOW_DIR=".claude/flow"
LOG_EVENT_SCRIPT="$(dirname "$0")/log-event.py"

# Extract tool input (the agent spawn request)
TOOL_INPUT=$(echo "$INPUT" | sed -n 's/.*"tool_input"[[:space:]]*:[[:space:]]*"\(.*\)"/\1/p' | head -1)

# Check what kind of agent is being spawned
if echo "$TOOL_INPUT" | grep -q 'scout'; then
  # Scout can be invoked anytime — no restriction
  exit 0
fi

if echo "$TOOL_INPUT" | grep -q 'forge'; then
  # Forge needs an approved plan (standalone requests are fine too — no restriction)
  exit 0
fi

if echo "$TOOL_INPUT" | grep -q 'sentinel'; then
  # Sentinel should have files to review
  if [ ! -f "$FLOW_DIR/modified-files.txt" ] || [ ! -s "$FLOW_DIR/modified-files.txt" ]; then
    # Log the guard block event
    python "$LOG_EVENT_SCRIPT" tool_guard_block "guard=pre-agent" "agent=sentinel" "reason=no_modified_files" 2>/dev/null || true
    echo '{"decision":"block","reason":"No modified files to review. Run implementation first, or use /code-review for specific files."}' >&2
    exit 2
  fi
fi

exit 0
