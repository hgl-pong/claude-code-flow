#!/usr/bin/env bash
# E2E test: brainstorming skill
# Verifies Claude understands the diverge/converge pattern and approval gate.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-180}"

echo "=== Test: brainstorming skill ==="
echo ""

# ------------------------------------------------------------------
# Test 1: Skill is recognized
# ------------------------------------------------------------------
echo "Test 1: Skill recognized and describes diverge/converge..."
output="$(run_claude \
  "What does the brainstorming skill do? Describe its phases." \
  "$timeout_seconds")"
assert_contains "$output" "brainstorm" "skill name present"
assert_contains "$output" "diverge|divergent|explore|options|alternatives" "mentions divergent thinking"
assert_contains "$output" "converge|convergent|recommend|select|choose" "mentions convergent thinking"
echo ""

# ------------------------------------------------------------------
# Test 2: Approval gate is mandatory
# ------------------------------------------------------------------
echo "Test 2: Approval gate before implementation..."
output="$(run_claude \
  "In the brainstorming skill, can implementation begin before the user approves a design? Why or why not?" \
  "$timeout_seconds")"
assert_contains "$output" "no|must.*approve|require.*approval|wait.*approval|cannot.*before" \
  "Blocks implementation without approval"
assert_contains "$output" "user.*approve|human.*approve|approval" "Requires human approval"
echo ""

# ------------------------------------------------------------------
# Test 3: What triggers brainstorming
# ------------------------------------------------------------------
echo "Test 3: Correct triggers for brainstorming..."
output="$(run_claude \
  "According to the brainstorming skill, what kinds of tasks REQUIRE brainstorming before coding?" \
  "$timeout_seconds")"
assert_contains "$output" "new feature|architecture|UI|refactor|broad|non-trivial" "Lists correct triggers"
echo ""

# ------------------------------------------------------------------
# Test 4: Output artifact
# ------------------------------------------------------------------
echo "Test 4: Output artifact described..."
output="$(run_claude \
  "What artifact does the brainstorming skill produce at the end?" \
  "$timeout_seconds")"
assert_contains "$output" "design.*doc|spec|proposal|recommendation|decision" "Produces a design artifact"
echo ""

echo "=== All brainstorming skill tests passed ==="
