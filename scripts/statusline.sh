#!/bin/bash
# Claude Code Flow statusline — workflow phase, task progress, git info
# Configure in settings.json:
#   "statusLine": { "type": "command", "command": "bash <path-to-this-script>" }

FLOW_DIR=".claude/flow"
STATE_FILE="$FLOW_DIR/workflow-state.json"
ULW_STATE_FILE="$FLOW_DIR/ulw-state.json"
TRACK_FILE="$FLOW_DIR/modified-files.txt"
LAST_VERIFICATION="$FLOW_DIR/last-verification.json"

# --- Git info ---
GIT_INFO=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  BRANCH=$(git branch --show-current 2>/dev/null)
  AHEAD=$(git rev-list --count "@{upstream}..HEAD" 2>/dev/null || echo "0")
  BEHIND=$(git rev-list --count "HEAD..@{upstream}" 2>/dev/null || echo "0")
  if [ "$AHEAD" -gt 0 ] || [ "$BEHIND" -gt 0 ]; then
    GIT_INFO=" $BRANCH +${AHEAD}/-${BEHIND}"
  else
    GIT_INFO=" $BRANCH"
  fi
fi

# --- ULW (Ultrawork) active state — shown instead of normal flow status ---
if [ -f "$ULW_STATE_FILE" ]; then
  ULW_ACTIVE=$(sed -n 's/.*"active"[[:space:]]*:[[:space:]]*\([a-z]*\).*/\1/p' "$ULW_STATE_FILE" | head -1)
  if [ "$ULW_ACTIVE" = "true" ]; then
    ULW_INTENT=$(sed -n 's/.*"intent"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$ULW_STATE_FILE" | head -1)
    ULW_DONE=$(sed -n 's/.*"task_done"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' "$ULW_STATE_FILE" | head -1)
    ULW_TOTAL=$(sed -n 's/.*"task_total"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' "$ULW_STATE_FILE" | head -1)
    ULW_ITER=$(sed -n 's/.*"iteration"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' "$ULW_STATE_FILE" | head -1)

    ULW_PROGRESS=""
    if [ -n "$ULW_TOTAL" ] && [ "$ULW_TOTAL" -gt 0 ]; then
      ULW_PROGRESS=" ${ULW_DONE}/${ULW_TOTAL}"
    fi

    ULW_LOOP=""
    if [ -n "$ULW_ITER" ] && [ "$ULW_ITER" -gt 0 ]; then
      ULW_LOOP=" #${ULW_ITER}"
    fi

    VERIFY=""
    if [ -f "$LAST_VERIFICATION" ]; then
      VERIFY_STATUS=$(sed -n 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$LAST_VERIFICATION" | head -1)
      case "$VERIFY_STATUS" in
        pass) VERIFY=" ok" ;;
        fail) VERIFY=" fail" ;;
      esac
    fi

    echo "⚡ulw:${ULW_INTENT:-?}${ULW_PROGRESS}${ULW_LOOP}${VERIFY}${GIT_INFO}"
    exit 0
  fi
fi

# --- Normal workflow phase from state file ---
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

  VERIFY=""
  if [ -f "$LAST_VERIFICATION" ]; then
    VERIFY_STATUS=$(sed -n 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$LAST_VERIFICATION" | head -1)
    case "$VERIFY_STATUS" in
      pass) VERIFY=" ok" ;;
      fail) VERIFY=" fail" ;;
      *) VERIFY="" ;;
    esac
  fi

  echo "flow:${PHASE_DISPLAY}${PROGRESS}${VERIFY}${GIT_INFO}"
else
  # No workflow state — show git info + modified files
  if [ -f "$TRACK_FILE" ] && [ -s "$TRACK_FILE" ]; then
    COUNT=$(wc -l < "$TRACK_FILE" | tr -d ' ')
    echo "flow:idle ${COUNT} files${GIT_INFO}"
  else
    echo "flow:idle${GIT_INFO}"
  fi
fi
