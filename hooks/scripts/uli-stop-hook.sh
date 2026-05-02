#!/bin/bash
# ULI (Ultra Loop Iteration) Stop Hook
# Prevents Claude from exiting when a ULI session is active and not yet complete.
#
# Mechanism (same pattern as ulw-stop-hook.sh):
#   1. On Stop event, read .claude/flow/uli-state.json
#   2. If ULI is active and Claude's last message lacks <uli-done>, block exit
#   3. Re-inject a fixed ULI continuation prompt so Claude continues the iteration loop
#   4. Claude must output <uli-done>SUMMARY</uli-done> to exit
#
# Key difference from ulw-stop-hook.sh:
#   - Reads uli-state.json (not ulw-state.json)
#   - Completion signal is <uli-done> (not <ulw-done>)
#   - max_iterations default is 10 (not 25) — each iteration is a full dev cycle
#   - Re-injected prompt is a fixed ULI continuation message, not the original user prompt
#   - Aware of iteration sub-phases: pd_generating → dev_pipeline → acceptance → next_iteration
#
# uli-state.json schema:
# {
#   "active": true,
#   "session_id": "<claude session id>",
#   "goal": "<product goal from user prompt or README>",
#   "iteration": 1,
#   "max_iterations": 10,
#   "current_phase": "pd_generating|dev_pipeline|acceptance|complete",
#   "pd_proposal_ready": false,
#   "acceptance_status": null,
#   "started_at": "<iso timestamp>",
#   "last_iteration_at": "<iso timestamp>"
# }

set -euo pipefail

HOOK_INPUT=$(cat)
ULI_STATE_FILE=".claude/flow/uli-state.json"

# ── 1. No state file → ULI not active, allow exit ─────────────────────────
if [[ ! -f "$ULI_STATE_FILE" ]]; then
  exit 0
fi

# ── 2. Parse state ──────────────────────────────────────────────────────────
ACTIVE=$(jq -r '.active // false' "$ULI_STATE_FILE")
if [[ "$ACTIVE" != "true" ]]; then
  exit 0
fi

# Session isolation: only the session that started ULI may be blocked
STATE_SESSION=$(jq -r '.session_id // ""' "$ULI_STATE_FILE")
HOOK_SESSION=$(echo "$HOOK_INPUT" | jq -r '.session_id // ""')
if [[ -n "$STATE_SESSION" ]] && [[ "$STATE_SESSION" != "$HOOK_SESSION" ]]; then
  exit 0
fi

ITERATION=$(jq -r '.iteration // 1' "$ULI_STATE_FILE")
MAX_ITERATIONS=$(jq -r '.max_iterations // 10' "$ULI_STATE_FILE")
GOAL=$(jq -r '.goal // "continue product development"' "$ULI_STATE_FILE")
CURRENT_PHASE=$(jq -r '.current_phase // "pd_generating"' "$ULI_STATE_FILE")

# ── 3. Max iterations guard ────────────────────────────────────────────────
if [[ $MAX_ITERATIONS -gt 0 ]] && [[ $ITERATION -gt $MAX_ITERATIONS ]]; then
  echo "ULI: Max iterations ($MAX_ITERATIONS) reached. Stopping."
  jq '.active = false' "$ULI_STATE_FILE" > "${ULI_STATE_FILE}.tmp" && mv "${ULI_STATE_FILE}.tmp" "$ULI_STATE_FILE"
  exit 0
fi

# ── 4. Check for completion tag in transcript ──────────────────────────────
TRANSCRIPT_PATH=$(echo "$HOOK_INPUT" | jq -r '.transcript_path // ""')

if [[ -z "$TRANSCRIPT_PATH" ]] || [[ ! -f "$TRANSCRIPT_PATH" ]]; then
  echo "WARNING: ULI: Transcript not found, stopping." >&2
  jq '.active = false' "$ULI_STATE_FILE" > "${ULI_STATE_FILE}.tmp" && mv "${ULI_STATE_FILE}.tmp" "$ULI_STATE_FILE"
  exit 0
fi

# Extract last assistant text from JSONL transcript
set +e
LAST_OUTPUT=$(grep '"role":"assistant"' "$TRANSCRIPT_PATH" | tail -n 100 | \
  jq -rs 'map(.message.content[]? | select(.type == "text") | .text) | last // ""' 2>/dev/null)
JQ_EXIT=$?
set -e

if [[ $JQ_EXIT -ne 0 ]]; then
  echo "WARNING: ULI: Could not parse transcript, letting Claude continue." >&2
  exit 0
fi

# Check for <uli-done> tag
if echo "$LAST_OUTPUT" | grep -q '<uli-done>'; then
  DONE_SUMMARY=$(echo "$LAST_OUTPUT" | \
    perl -0777 -pe 's/.*?<uli-done>(.*?)<\/uli-done>.*/$1/s; s/^\s+|\s+$//g' 2>/dev/null || echo "complete")
  echo "ULI: All iterations complete — $DONE_SUMMARY"
  jq --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
     '.active = false | .completed_at = $ts' \
     "$ULI_STATE_FILE" > "${ULI_STATE_FILE}.tmp" && mv "${ULI_STATE_FILE}.tmp" "$ULI_STATE_FILE"
  exit 0
fi

# ── 5. Not done yet — block exit and re-inject ULI continuation ────────────

# Do NOT increment iteration here — iteration only advances after acceptance passes.
# The iteration counter is managed by flow-state.py uli-next, called only after ACCEPT.

# Build phase-aware re-injection message
case "$CURRENT_PHASE" in
  "pd_generating")
    PHASE_MSG="PD must generate a NEW proposal for this iteration. Continue: spawn pd agent (it reads product-state.md and uli-acceptance-report.md), wait for uli-proposal.md with at least 1 CORE requirement, then proceed to oracle plan."
    ;;
  "dev_pipeline")
    PHASE_MSG="The dev pipeline is still in progress for iteration ${ITERATION}. Continue: complete ALL implementation tasks for this iteration, run sentinel review (two-stage), then run validator acceptance. Do NOT advance to next iteration until acceptance passes."
    ;;
  "acceptance")
    PHASE_MSG="Acceptance gate is pending for iteration ${ITERATION}. Continue: run validator, check build + tests + feature checklist against uli-proposal.md, record result. Only on ACCEPT: commit, update product-state.md, increment iteration via uli-next, then spawn PD for next iteration."
    ;;
  *)
    PHASE_MSG="Continue the ULI iteration loop for iteration ${ITERATION}: PD proposal exists → implement ALL tasks → sentinel review → hard acceptance → commit → increment → PD for next iteration."
    ;;
esac

# ── 5a. Stuck detection ──────────────────────────────────────────────────────
STUCK_FILE=".claude/flow/uli-stuck-tracker.json"
STUCK_MSG=""

PREV_PHASE=""
STUCK_COUNT=0
if [[ -f "$STUCK_FILE" ]]; then
  PREV_PHASE=$(jq -r '.current_phase // ""' "$STUCK_FILE")
  STUCK_COUNT=$(jq -r '.stuck_count // 0' "$STUCK_FILE")
fi

if [[ "$CURRENT_PHASE" == "$PREV_PHASE" ]] && [[ "$CURRENT_PHASE" != "complete" ]]; then
  STUCK_COUNT=$((STUCK_COUNT + 1))
  if [[ $STUCK_COUNT -ge 3 ]]; then
    STUCK_MSG=" WARNING: Stuck in '${CURRENT_PHASE}' phase for ${STUCK_COUNT} iterations. Consider escalating or adjusting the approach. Do NOT emit <uli-done> unless the product goal is fully delivered."
  fi
else
  STUCK_COUNT=0
fi

jq -n --arg p "$CURRENT_PHASE" --argjson s "$STUCK_COUNT" \
  '{current_phase: $p, stuck_count: $s}' > "$STUCK_FILE"

# ── 5b. Product state summary ────────────────────────────────────────────────
PRODUCT_STATE_MSG=""
PRODUCT_STATE_FILE=".claude/flow/uli/product-state.md"
if [[ -f "$PRODUCT_STATE_FILE" ]]; then
  PRODUCT_SUMMARY=$(head -c 500 "$PRODUCT_STATE_FILE" 2>/dev/null || echo "")
  if [[ -n "$PRODUCT_SUMMARY" ]]; then
    PRODUCT_STATE_MSG=" | Product state: $(echo "$PRODUCT_SUMMARY" | head -3 | tr '\n' ' ')"
  fi
fi

SYSTEM_MSG="ULI iteration ${ITERATION}/${MAX_ITERATIONS} | goal: ${GOAL} | phase: ${CURRENT_PHASE} | ${PHASE_MSG}${PRODUCT_STATE_MSG}${STUCK_MSG} | Output <uli-done>SUMMARY</uli-done> ONLY when all iterations are complete or the product goal is fully delivered."

CONTINUATION_PROMPT="Continue ULI iteration ${ITERATION}. Goal: ${GOAL}. Phase: ${CURRENT_PHASE}. ONE ITERATION = one PD proposal + all tasks delivered + acceptance passed + commit. Do NOT treat individual tasks as iterations. Read .claude/flow/uli-state.json, .claude/flow/uli-proposal.md, and .claude/flow/uli-acceptance-report.md to understand where to resume, then continue the ultrawork skill ULI branch."

jq -n \
  --arg prompt "$CONTINUATION_PROMPT" \
  --arg msg "$SYSTEM_MSG" \
  '{
    "decision": "block",
    "reason": $prompt,
    "systemMessage": $msg
  }'

exit 0
