#!/bin/bash
# Manage workflow state file
# Usage: flow-state.sh <action> [args]
#   set-phase <phase>          — Set workflow phase (plan/design/impl/review/idle)
#   set-tasks <done> <total>   — Set task progress
#   clear                      — Clear workflow state

FLOW_DIR=".claude/flow"
STATE_FILE="$FLOW_DIR/workflow-state.json"
mkdir -p "$FLOW_DIR"

init_state() {
  echo '{"phase":"idle","task_done":0,"task_total":0,"updated_at":""}' > "$STATE_FILE"
}

if [ ! -f "$STATE_FILE" ]; then
  init_state
fi

ACTION="$1"
shift 2>/dev/null

case "$ACTION" in
  set-phase)
    PHASE="$1"
    sed -i.bak "s/\"phase\":\"[^\"]*\"/\"phase\":\"$PHASE\"/" "$STATE_FILE" 2>/dev/null
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
    sed -i.bak "s/\"updated_at\":\"[^\"]*\"/\"updated_at\":\"$TIMESTAMP\"/" "$STATE_FILE" 2>/dev/null
    rm -f "$STATE_FILE.bak"
    ;;
  set-tasks)
    DONE="$1"
    TOTAL="$2"
    sed -i.bak "s/\"task_done\":[0-9]*/\"task_done\":$DONE/" "$STATE_FILE" 2>/dev/null
    sed -i.bak "s/\"task_total\":[0-9]*/\"task_total\":$TOTAL/" "$STATE_FILE" 2>/dev/null
    rm -f "$STATE_FILE.bak"
    ;;
  clear)
    init_state
    rm -f "$FLOW_DIR/modified-files.txt" "$FLOW_DIR/review-result.txt"
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    exit 1
    ;;
esac
