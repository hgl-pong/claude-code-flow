#!/usr/bin/env bash
# E2E test: writing-plans skill
# Verifies Claude understands plan structure, task atomicity, and test-first requirements.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-180}"

echo "=== Test: writing-plans skill ==="
echo ""

# ------------------------------------------------------------------
# Test 1: Skill recognized
# ------------------------------------------------------------------
echo "Test 1: Skill recognized and key concepts described..."
output="$(run_claude \
  "What is the writing-plans skill? What does a good plan look like according to it?" \
  "$timeout_seconds")"
assert_contains "$output" "writing-plans|write.*plan" "skill name present"
assert_contains "$output" "task|step|breakdown" "mentions tasks/breakdown"
echo ""

# ------------------------------------------------------------------
# Test 2: Test-first requirement in tasks
# ------------------------------------------------------------------
echo "Test 2: Test-first embedded in tasks..."
output="$(run_claude \
  "In writing-plans, should tests be written before or after implementation for each task? How is this reflected in a plan?" \
  "$timeout_seconds")"
assert_contains "$output" "before|test.*first|TDD|failing.*test|write.*test.*before" \
  "Tests before implementation"
echo ""

# ------------------------------------------------------------------
# Test 3: Atomic task size
# ------------------------------------------------------------------
echo "Test 3: Task atomicity..."
output="$(run_claude \
  "According to writing-plans, how large should each task in a plan be? What makes a task too large?" \
  "$timeout_seconds")"
assert_contains "$output" "small|atomic|single|focused|one.*thing|granular" "Emphasises small tasks"
echo ""

# ------------------------------------------------------------------
# Test 4: Verification step per task
# ------------------------------------------------------------------
echo "Test 4: Each task has a verification step..."
output="$(run_claude \
  "Does the writing-plans skill require each task to include a verification or acceptance step? Explain." \
  "$timeout_seconds")"
assert_contains "$output" "yes|verif|acceptance|confirm|check" "Verification step required"
echo ""

# ------------------------------------------------------------------
# Test 5: Plan requires approved design as input
# ------------------------------------------------------------------
echo "Test 5: Plan written from approved design..."
output="$(run_claude \
  "According to the writing-plans skill, what must exist before you can write an implementation plan?" \
  "$timeout_seconds")"
assert_contains "$output" "brainstorm|approved.*design|design.*doc|spec|requirement" \
  "Requires prior approved design"
echo ""

echo "=== All writing-plans skill tests passed ==="
