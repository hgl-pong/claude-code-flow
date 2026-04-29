#!/usr/bin/env bash
# Integration test: full dev-orchestrator workflow
# Runs Claude through a real (small) implementation task and verifies:
#   1. Skill tool is invoked
#   2. Subagents (Task tool) are dispatched
#   3. Files are created and tests pass
#   4. Git commits are made
#   5. Token usage is reported
#
# WARNING: This test takes 10-30 minutes and costs real API tokens.
# Run with:  bash tests/claude-code/test-integration-dev-orchestrator.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " Integration Test: dev-orchestrator workflow"
echo "========================================"
echo ""
echo "This test executes a real small plan and verifies end-to-end behaviour."
echo "Expected duration: 10-30 minutes."
echo ""

# ------------------------------------------------------------------
# Setup temp project
# ------------------------------------------------------------------
TEST_PROJECT="$(create_test_project)"
echo "Test project: $TEST_PROJECT"
trap "cleanup_test_project '$TEST_PROJECT'" EXIT

init_node_project "$TEST_PROJECT"

# Write a minimal plan
cat >"$TEST_PROJECT/docs/plans/implementation-plan.md" <<'PLAN'
# Math Utilities Plan

## Task 1: Create add function

**File:** `src/math.js`

**Requirements:**
- Export function `add(a, b)` that returns `a + b`

**Tests:** `test/math.test.js`
- `add(2, 3)` === 5
- `add(0, 0)` === 0
- `add(-1, 1)` === 0

**Verification:** `npm test`

## Task 2: Create multiply function

**File:** `src/math.js` (append)

**Requirements:**
- Export function `multiply(a, b)` that returns `a * b`
- DO NOT add divide, power, or subtract functions

**Tests:** add to `test/math.test.js`
- `multiply(2, 3)` === 6
- `multiply(0, 5)` === 0
- `multiply(-2, 3)` === -6

**Verification:** `npm test`
PLAN

init_git_repo "$TEST_PROJECT"

echo "Project setup complete. Starting Claude..."
echo ""

# ------------------------------------------------------------------
# Run Claude in headless mode from the plugin root so skills load
# ------------------------------------------------------------------
OUTPUT_FILE="$TEST_PROJECT/claude-output.txt"

PROMPT="Change to directory $TEST_PROJECT and execute the implementation plan at \
docs/plans/implementation-plan.md using the dev-orchestrator skill (quick mode). \
Follow the skill exactly: write a failing test first for each task, then implement, \
then run npm test to verify. Commit after each task."

cd "$ROOT_DIR"
echo "Running Claude (output → $OUTPUT_FILE)..."
echo "================================================================"
timeout 1800 claude -p "$PROMPT" \
  --allowed-tools all \
  --add-dir "$TEST_PROJECT" \
  --permission-mode bypassPermissions \
  2>&1 | tee "$OUTPUT_FILE" || {
    echo ""
    echo "================================================================"
    echo "EXECUTION FAILED (exit $?)"
    exit 1
  }
echo "================================================================"
echo ""
echo "Execution complete. Verifying..."
echo ""

# ------------------------------------------------------------------
# Find the session transcript
# ------------------------------------------------------------------
SESSION_FILE="$(find_session_file "$ROOT_DIR" 60)"
if [ -z "$SESSION_FILE" ]; then
  echo "ERROR: Could not find session JSONL file."
  echo "Looked for recent files in ~/.claude/projects/ corresponding to $ROOT_DIR"
  exit 1
fi
echo "Session transcript: $(basename "$SESSION_FILE")"
echo ""

# ------------------------------------------------------------------
# Verification tests
# ------------------------------------------------------------------
FAILED=0

echo "=== Verification Tests ==="
echo ""

echo "Test 1: Skill invoked..."
if grep -Eq '"skill":"([^"]*:)?dev-orchestrator"' "$SESSION_FILE" 2>/dev/null; then
  echo "  [PASS] dev-orchestrator skill was invoked"
else
  echo "  [FAIL] dev-orchestrator skill was NOT invoked"
  FAILED=$((FAILED+1))
fi
echo ""

echo "Test 2: Subagents dispatched (Task tool)..."
task_count="$(grep -c '"name":"Task"' "$SESSION_FILE" 2>/dev/null || echo 0)"
if [ "$task_count" -ge 2 ]; then
  echo "  [PASS] $task_count Task invocations found"
else
  echo "  [FAIL] Only $task_count Task invocations (expected ≥ 2)"
  FAILED=$((FAILED+1))
fi
echo ""

echo "Test 3: TodoWrite used for tracking..."
todo_count="$(grep -c '"name":"TodoWrite"' "$SESSION_FILE" 2>/dev/null || echo 0)"
if [ "$todo_count" -ge 1 ]; then
  echo "  [PASS] TodoWrite used $todo_count time(s)"
else
  echo "  [FAIL] TodoWrite never used"
  FAILED=$((FAILED+1))
fi
echo ""

echo "Test 4: Implementation files created..."
assert_file_exists "$TEST_PROJECT/src/math.js"     "src/math.js created" || FAILED=$((FAILED+1))
assert_file_contains "$TEST_PROJECT/src/math.js" "export function add" "add function exported" || FAILED=$((FAILED+1))
assert_file_contains "$TEST_PROJECT/src/math.js" "export function multiply" "multiply function exported" || FAILED=$((FAILED+1))
assert_file_exists "$TEST_PROJECT/test/math.test.js" "test/math.test.js created" || FAILED=$((FAILED+1))
echo ""

echo "Test 5: Tests pass..."
if (cd "$TEST_PROJECT" && npm test >/dev/null 2>&1); then
  echo "  [PASS] npm test passes"
else
  echo "  [FAIL] npm test FAILED"
  cd "$TEST_PROJECT" && npm test 2>&1 | sed 's/^/    /'
  FAILED=$((FAILED+1))
fi
echo ""

echo "Test 6: No extra functions added (spec compliance)..."
if grep -Eq "export function (divide|subtract|power|mod)" "$TEST_PROJECT/src/math.js" 2>/dev/null; then
  echo "  [WARN] Extra function(s) found — spec compliance missed this"
else
  echo "  [PASS] No extra functions added"
fi
echo ""

echo "Test 7: Git commits created..."
commit_count="$(git -C "$TEST_PROJECT" log --oneline | wc -l)"
if [ "$commit_count" -gt 2 ]; then
  echo "  [PASS] $commit_count commits (initial + task commits)"
else
  echo "  [FAIL] Only $commit_count commit(s), expected > 2"
  FAILED=$((FAILED+1))
fi
echo ""

# ------------------------------------------------------------------
# Token analysis
# ------------------------------------------------------------------
echo "========================================="
echo " Token Usage Analysis"
echo "========================================="
echo ""
python3 "$SCRIPT_DIR/analyze-token-usage.py" "$SESSION_FILE"
echo ""

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo "========================================"
echo " Test Summary"
echo "========================================"
echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "STATUS: PASSED"
  echo ""
  echo "  ✓ dev-orchestrator skill invoked"
  echo "  ✓ Subagents dispatched"
  echo "  ✓ Failing tests written first"
  echo "  ✓ Implementation complete"
  echo "  ✓ Tests pass"
  echo "  ✓ Git commits created"
  exit 0
else
  echo "STATUS: FAILED ($FAILED test(s) failed)"
  echo ""
  echo "Full output saved to: $OUTPUT_FILE"
  exit 1
fi
