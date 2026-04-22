#!/bin/bash
# Claude Code Flow statusline — workflow phase, task progress, git info
# Configure in settings.json:
#   "statusLine": { "type": "command", "command": "bash <path-to-this-script>" }

FLOW_DIR=".claude/flow"
STATE_FILE="$FLOW_DIR/workflow-state.json"
TRACK_FILE="$FLOW_DIR/modified-files.txt"

# --- Git info ---
GIT_INFO=""
if git rev-parse --is-inside-work-tree 2>/dev/null; then
  BRANCH=$(git branch --show-current 2>/dev/null)
  AHEAD=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo "0")
  BEHIND=$(git rev-list --count "HEAD..@{upstream}" 2>/dev/null || echo "0")
  if [ "$AHEAD" -gt 0 ] || [ "$BEHIND" -gt 0 ]; then
    GIT_INFO=" $BRANCH +${AHEAD}/-${BEHIND}"
  else
    GIT_INFO=" $BRANCH"
  fi
fi

# --- Workflow phase from state file ---
if [ -f "$STATE_FILE" ]; then
  PHASE=$(sed -n 's/.*"phase"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$STATE_FILE" | head -1)
  TASK_TOTAL=$(sed -n 's/.*"task_total"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' "$STATE_FILE" | head -1)
  TASK_DONE=$(sed -n 's/.*"task_done"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' "$STATE_FILE" | head -1)

  case "$PHASE" in
    plan|design|impl|review) PHASE_DISPLAY="$PHASE" ;;
    *) PHASE_DISPLAY="idle" ;;
  esac

  if [ -n "$TASK_TOTAL" ] && [ "$TASK_TOTAL" -gt 0 ]; then
    PROGRESS=" ${TASK_DONE}/${TASK_TOTAL}"
  else
    PROGRESS=""
  fi

  echo "flow:${PHASE_DISPLAY}${PROGRESS}${GIT_INFO}"
else
  # No workflow state — show git info + modified files
  if [ -f "$TRACK_FILE" ] && [ -s "$TRACK_FILE" ]; then
    COUNT=$(wc -l < "$TRACK_FILE" | tr -d ' ')
    echo "flow:idle ${COUNT} files${GIT_INFO}"
  else
    echo "flow:idle${GIT_INFO}"
  fi
fi
