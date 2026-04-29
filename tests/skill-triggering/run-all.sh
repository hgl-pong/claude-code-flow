#!/usr/bin/env bash
# Run all skill-triggering tests.
# Tests verify that natural-language prompts cause Claude to load the right skill.
#
# Usage:
#   ./run-all.sh [--verbose] [--skill <skill-name>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VERBOSE=false
FILTER=""

while [ $# -gt 0 ]; do
  case "$1" in
    --verbose|-v) VERBOSE=true; shift ;;
    --skill)      FILTER="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: $0 [--verbose] [--skill <name>]"
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

# skill-name → prompt file
declare -A TESTS=(
  ["brainstorming"]="prompts/brainstorming.txt"
  ["writing-plans"]="prompts/writing-plans.txt"
  ["systematic-debugging"]="prompts/systematic-debugging.txt"
  ["verification-before-completion"]="prompts/verification-before-completion.txt"
  ["testing-strategy"]="prompts/testing-strategy.txt"
)

passed=0; failed=0; skipped=0

echo "========================================"
echo " Skill-Triggering Tests"
echo "========================================"
echo "Repository: $(cd "$SCRIPT_DIR/../.." && pwd)"
echo ""

for skill in "${!TESTS[@]}"; do
  [ -n "$FILTER" ] && [ "$skill" != "$FILTER" ] && continue

  prompt_file="$SCRIPT_DIR/${TESTS[$skill]}"
  echo "----------------------------------------"
  echo "Skill: $skill"
  echo "----------------------------------------"

  if [ ! -f "$prompt_file" ]; then
    echo "  [SKIP] prompt file not found: $prompt_file"
    skipped=$((skipped+1))
    continue
  fi

  if [ "$VERBOSE" = true ]; then
    if bash "$SCRIPT_DIR/run-test.sh" "$skill" "$prompt_file"; then
      passed=$((passed+1))
    else
      code=$?
      [ "$code" -eq 77 ] && skipped=$((skipped+1)) || failed=$((failed+1))
    fi
  else
    if output=$(bash "$SCRIPT_DIR/run-test.sh" "$skill" "$prompt_file" 2>&1); then
      echo "  [PASS]"
      passed=$((passed+1))
    else
      code=$?
      if [ "$code" -eq 77 ]; then
        echo "  [SKIP]"
        skipped=$((skipped+1))
      else
        echo "  [FAIL]"
        printf '%s\n' "$output" | sed 's/^/    /'
        failed=$((failed+1))
      fi
    fi
  fi
  echo ""
done

echo "========================================"
echo " Results"
echo "========================================"
echo "Passed:  $passed"
echo "Failed:  $failed"
echo "Skipped: $skipped"

[ "$failed" -eq 0 ] && exit 0 || exit 1
