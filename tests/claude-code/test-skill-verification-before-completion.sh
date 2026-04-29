#!/usr/bin/env bash
# E2E test: verification-before-completion skill
# Verifies Claude understands fresh-evidence, no-claimed-success, and checklist gating.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-180}"

echo "=== Test: verification-before-completion skill ==="
echo ""

# ------------------------------------------------------------------
# Test 1: Skill recognized and fresh-evidence concept present
# ------------------------------------------------------------------
echo "Test 1: Fresh evidence required..."
output="$(run_claude \
  "What does the verification-before-completion skill mean by 'fresh evidence'?" \
  "$timeout_seconds")"
assert_contains "$output" "fresh.*evidence|new.*evidence|recent.*evidence|re-run|actually.*ran|just.*ran" \
  "Explains fresh evidence"
assert_not_contains "$output" "claimed|assumed|told" "Does not accept claimed success"
echo ""

# ------------------------------------------------------------------
# Test 2: Cannot mark done without running checks
# ------------------------------------------------------------------
echo "Test 2: Must actually run verification, not rely on memory..."
output="$(run_claude \
  "In verification-before-completion, can you report a task as complete based on what you remember running earlier? Why or why not?" \
  "$timeout_seconds")"
assert_contains "$output" "no|must.*run|re-run|actual.*run|cannot.*assum|not.*sufficient" \
  "Disallows memory-based completion"
echo ""

# ------------------------------------------------------------------
# Test 3: Verification checklist items
# ------------------------------------------------------------------
echo "Test 3: Verification checklist covers tests, lint, types..."
output="$(run_claude \
  "List all the things the verification-before-completion skill requires you to verify before closing a task." \
  "$timeout_seconds")"
assert_contains "$output" "test|pass" "Mentions tests passing"
assert_contains "$output" "lint|style|format" "Mentions lint/style"
assert_contains "$output" "type|compile|build" "Mentions type/build checks"
echo ""

# ------------------------------------------------------------------
# Test 4: When to use this skill
# ------------------------------------------------------------------
echo "Test 4: Used at end of every task..."
output="$(run_claude \
  "When exactly should you invoke verification-before-completion? Is it optional?" \
  "$timeout_seconds")"
assert_contains "$output" "every.*task|each.*task|before.*complet|before.*clos|before.*done|always" \
  "Required before every task completion"
echo ""

echo "=== All verification-before-completion skill tests passed ==="
