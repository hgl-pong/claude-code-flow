#!/usr/bin/env bash
# Test: skill triggering via natural-language prompts
# Verifies that Claude invokes the correct skill when the user does NOT explicitly
# name it — just describes their problem in plain language.
#
# Usage:
#   ./run-test.sh <skill-name> <prompt-file> [max-turns]
#
# Exit codes:
#   0   — skill triggered
#   1   — skill NOT triggered
#   77  — Claude CLI unavailable (skip)

set -e

SKILL_NAME="$1"
PROMPT_FILE="$2"
MAX_TURNS="${3:-3}"

if [ -z "$SKILL_NAME" ] || [ -z "$PROMPT_FILE" ]; then
  echo "Usage: $0 <skill-name> <prompt-file> [max-turns]"
  echo "Example: $0 brainstorming ./prompts/brainstorming.txt"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

TIMESTAMP=$(date +%s)
OUTPUT_DIR="/tmp/claude-code-flow-tests/${TIMESTAMP}/skill-triggering/${SKILL_NAME}"
mkdir -p "$OUTPUT_DIR"

PROMPT=$(cat "$PROMPT_FILE")

echo "=== Skill Triggering Test ==="
echo "Skill:       $SKILL_NAME"
echo "Prompt file: $PROMPT_FILE"
echo "Max turns:   $MAX_TURNS"
echo "Output dir:  $OUTPUT_DIR"
echo ""

cp "$PROMPT_FILE" "$OUTPUT_DIR/prompt.txt"

LOG_FILE="$OUTPUT_DIR/claude-output.json"
cd "$OUTPUT_DIR"

echo "Running claude -p with natural-language prompt..."
if ! timeout 300 claude -p "$PROMPT" \
    --dangerously-skip-permissions \
    --max-turns "$MAX_TURNS" \
    --output-format stream-json \
    >"$LOG_FILE" 2>&1; then

  # Infrastructure failure → SKIP
  if grep -Eiq "API Error|ECONNRESET|Unable to connect|network error|ETIMEDOUT|ENOTFOUND" "$LOG_FILE"; then
    echo "SKIP: Claude Code model/API unavailable."
    exit 77
  fi
fi

echo ""
echo "=== Results ==="

# Match "skill":"<name>" or "skill":"<namespace>:<name>"
SKILL_PATTERN="\"skill\":\"([^\"]*:)?${SKILL_NAME}\""
if grep -q '"name":"Skill"' "$LOG_FILE" && grep -qE "$SKILL_PATTERN" "$LOG_FILE"; then
  echo "PASS: Skill '$SKILL_NAME' was triggered"
  TRIGGERED=true
else
  echo "FAIL: Skill '$SKILL_NAME' was NOT triggered"
  TRIGGERED=false
fi

echo ""
echo "Skills triggered in this run:"
grep -o '"skill":"[^"]*"' "$LOG_FILE" 2>/dev/null | sort -u || echo "  (none)"

# Warn if Claude acted before loading the skill
echo ""
echo "Checking for premature action before skill invocation..."
FIRST_SKILL_LINE=$(grep -n '"name":"Skill"' "$LOG_FILE" 2>/dev/null | head -1 | cut -d: -f1 || true)
if [ -n "$FIRST_SKILL_LINE" ]; then
  PREMATURE=$(head -n "$FIRST_SKILL_LINE" "$LOG_FILE" \
    | grep '"type":"tool_use"' \
    | grep -v '"name":"Skill"' \
    | grep -v '"name":"TodoWrite"' || true)
  if [ -n "$PREMATURE" ]; then
    echo "WARNING: Tool(s) invoked BEFORE the Skill tool:"
    echo "$PREMATURE" | head -5
  else
    echo "OK: No premature tool invocations"
  fi
else
  echo "WARNING: No Skill tool invocation found at all"
fi

echo ""
echo "First assistant response (truncated):"
grep '"type":"assistant"' "$LOG_FILE" \
  | head -1 \
  | jq -r '.message.content[0].text // .message.content' 2>/dev/null \
  | head -c 500 \
  || echo "  (could not extract)"

echo ""
echo "Full log: $LOG_FILE"

if [ "$TRIGGERED" = "true" ]; then exit 0; else exit 1; fi
