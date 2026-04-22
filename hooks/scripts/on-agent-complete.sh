#!/bin/bash
# Called on SubagentStop — log agent completion
FLOW_DIR=".claude/flow"
LOG_FILE="$FLOW_DIR/agent-log.txt"

mkdir -p "$FLOW_DIR"

INPUT=$(cat)
AGENT_NAME=$(echo "$INPUT" | sed -n 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)

if [ -n "$AGENT_NAME" ]; then
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
  echo "[$TIMESTAMP] $AGENT_NAME completed" >> "$LOG_FILE"
fi
