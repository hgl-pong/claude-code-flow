#!/bin/bash
# ULW (Ultrawork) Stop Hook
# Prevents Claude from exiting when a ULW session is active and not yet complete.
#
# Mechanism (same pattern as ralph-loop):
#   1. On Stop event, read .claude/flow/ulw-state.json
#   2. If ULW is active and Claude's last message lacks <ulw-done>, block exit
#   3. Re-inject the original ULW prompt so Claude keeps working
#   4. Claude must output <ulw-done>TASK_SUMMARY</ulw-done> to exit
#
# ulw-state.json schema:
# {
#   "active": true,
#   "session_id": "<claude session id>",
#   "intent": "implement|fix|refactor|research|explain|test",
#   "prompt": "<original user prompt>",
#   "task_done": 0,
#   "task_total": 0,
#   "iteration": 0,
#   "max_iterations": 25,
#   "started_at": "<iso timestamp>"
# }

set -euo pipefail

HOOK_INPUT=$(cat)
ULW_STATE_FILE=".claude/flow/ulw-state.json"

# ── 1. No state file → ULW not active, allow exit ─────────────────────────
if [[ ! -f "$ULW_STATE_FILE" ]]; then
  exit 0
fi

# ── 2. Parse state ──────────────────────────────────────────────────────────
ACTIVE=$(jq -r '.active // false' "$ULW_STATE_FILE")
if [[ "$ACTIVE" != "true" ]]; then
  exit 0
fi

# Session isolation: only the session that started ULW may be blocked
STATE_SESSION=$(jq -r '.session_id // ""' "$ULW_STATE_FILE")
HOOK_SESSION=$(echo "$HOOK_INPUT" | jq -r '.session_id // ""')
if [[ -n "$STATE_SESSION" ]] && [[ "$STATE_SESSION" != "$HOOK_SESSION" ]]; then
  exit 0
fi

ITERATION=$(jq -r '.iteration // 0' "$ULW_STATE_FILE")
MAX_ITERATIONS=$(jq -r '.max_iterations // 25' "$ULW_STATE_FILE")
INTENT=$(jq -r '.intent // "implement"' "$ULW_STATE_FILE")
PROMPT_TEXT=$(jq -r '.prompt // ""' "$ULW_STATE_FILE")
TASK_DONE=$(jq -r '.task_done // 0' "$ULW_STATE_FILE")
TASK_TOTAL=$(jq -r '.task_total // 0' "$ULW_STATE_FILE")

# ── 3. Max iterations guard ────────────────────────────────────────────────
if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $ITERATION -ge $MAX_ITERATIONS ]]; then
  echo "🛑 ULW: Max iterations ($MAX_ITERATIONS) reached. Stopping."
  jq '.active = false' "$ULW_STATE_FILE" > "${ULW_STATE_FILE}.tmp" && mv "${ULW_STATE_FILE}.tmp" "$ULW_STATE_FILE"
  exit 0
fi

# ── 4. Check for completion tag in transcript ──────────────────────────────
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | jq -r '.transcript_path // ""')

if [[ -z "$TRANSCRIPT_PATH" ]] || [[ ! -f "$TRANSCRIPT_PATH" ]]; then
  echo "⚠️  ULW: Transcript not found, stopping." >&2
  jq '.active = false' "$ULW_STATE_FILE" > "${ULW_STATE_FILE}.tmp" && mv "${ULW_STATE_FILE}.tmp" "$ULW_STATE_FILE"
  exit 0
fi

# Extract last assistant text from JSONL transcript (same approach as ralph-loop)
set +e
LAST_OUTPUT=$(grep '"role":"assistant"' "$TRANSCRIPT_PATH" | tail -n 100 | \
  jq -rs 'map(.message.content[]? | select(.type == "text") | .text) | last // ""' 2>/dev/null)
JQ_EXIT=$?
set -e

if [[ $JQ_EXIT -ne 0 ]]; then
  # Parse error — let Claude continue rather than blocking forever
  echo "⚠️  ULW: Could not parse transcript, letting Claude continue." >&2
  exit 0
fi

# Check for <ulw-done> tag
if echo "$LAST_OUTPUT" | grep -q '<ulw-done>'; then
  # Extract summary for the final message
  DONE_SUMMARY=$(echo "$LAST_OUTPUT" | \
    perl -0777 -pe 's/.*?<ulw-done>(.*?)<\/ulw-done>.*/$1/s; s/^\s+|\s+$//g' 2>/dev/null || echo "complete")
  echo "✅ ULW: Task complete — $DONE_SUMMARY"
  # Mark inactive and record completion time
  jq --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     '.active = false | .completed_at = $ts' \
     "$ULW_STATE_FILE" > "${ULW_STATE_FILE}.tmp" && mv "${ULW_STATE_FILE}.tmp" "$ULW_STATE_FILE"
  exit 0
fi

# ── 5. Not done yet — block exit and re-inject prompt ─────────────────────
if [[ -z "$PROMPT_TEXT" ]]; then
  echo "⚠️  ULW: No prompt in state file, stopping." >&2
  jq '.active = false' "$ULW_STATE_FILE" > "${ULW_STATE_FILE}.tmp" && mv "${ULW_STATE_FILE}.tmp" "$ULW_STATE_FILE"
  exit 0
fi

NEXT_ITERATION=$((ITERATION + 1))

# Update iteration counter in state file
jq --argjson i "$NEXT_ITERATION" '.iteration = $i' \
  "$ULW_STATE_FILE" > "${ULW_STATE_FILE}.tmp" && mv "${ULW_STATE_FILE}.tmp" "$ULW_STATE_FILE"

# Build the re-injection system message
if [[ "$TASK_TOTAL" -gt 0 ]]; then
  PROGRESS_MSG="${TASK_DONE}/${TASK_TOTAL} tasks done"
else
  PROGRESS_MSG="tasks in progress"
fi

SYSTEM_MSG="⚡ ULW iteration $NEXT_ITERATION | intent:${INTENT} | ${PROGRESS_MSG} | Keep working until ALL tasks have fresh verification evidence. Output <ulw-done>SUMMARY</ulw-done> ONLY when everything is verified complete."

# Re-inject the original prompt (Claude sees its prior file-system work via context)
jq -n \
  --arg prompt "$PROMPT_TEXT" \
  --arg msg "$SYSTEM_MSG" \
  '{
    "decision": "block",
    "reason": $prompt,
    "systemMessage": $msg
  }'

exit 0
