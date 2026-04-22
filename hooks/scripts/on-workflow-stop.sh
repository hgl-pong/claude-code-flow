#!/bin/bash
# Called on Stop — persist workflow state summary
FLOW_DIR=".claude/flow"
SUMMARY_FILE="$FLOW_DIR/session-summary.txt"

mkdir -p "$FLOW_DIR"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")

if [ -f "$FLOW_DIR/workflow-state.json" ]; then
  PHASE=$(sed -n 's/.*"phase"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$FLOW_DIR/workflow-state.json" | head -1)
else
  PHASE="unknown"
fi

if [ -f "$FLOW_DIR/modified-files.txt" ] && [ -s "$FLOW_DIR/modified-files.txt" ]; then
  MODIFIED=$(wc -l < "$FLOW_DIR/modified-files.txt" | tr -d ' ')
else
  MODIFIED="0"
fi

echo "[$TIMESTAMP] phase=$PHASE | modified=$MODIFIED" >> "$SUMMARY_FILE"
