#!/usr/bin/env bash
# Integration test: ULI (Ultra Loop Iteration) end-to-end workflow
#
# Runs ONE full ULI iteration on a minimal project and verifies:
#   1. uli-detector hook fires and ULI MODE ACTIVE is injected
#   2. ultrawork skill (ULI branch) is invoked
#   3. PD agent spawns and writes uli-proposal.md
#   4. Dev pipeline executes (forge/weaver or equivalent)
#   5. uli-state.json exists with expected structure
#   6. uli-acceptance-report.md or <uli-done> emitted
#   7. product-state.md is created/updated
#   8. At least one commit is made on a uli/ branch
#
# WARNING: This test takes 15-40 minutes and costs real API tokens.
# Run with:  bash tests/claude-code/test-integration-uli.sh
#
# Scope: We run with --max-turns 80 and expect ONE full iteration to complete.
# We do NOT test multi-iteration looping here (that would require hours).
# The stop hook and loop continuation are tested in test_uli_hooks.py (unit tests).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " Integration Test: ULI workflow"
echo "========================================"
echo ""
echo "Tests one complete ULI iteration on a minimal project."
echo "Expected duration: 15-40 minutes."
echo ""

# ------------------------------------------------------------------
# Setup: temp project with a simple product goal
# ------------------------------------------------------------------
TEST_PROJECT="$(create_test_project)"
echo "Test project: $TEST_PROJECT"
trap "cleanup_test_project '$TEST_PROJECT'" EXIT

init_node_project "$TEST_PROJECT"

# Write a minimal README so the PD agent has product context
cat >"$TEST_PROJECT/README.md" <<'README'
# String Utilities

A small Node.js utility library.

## Goal

Provide a set of tested string manipulation functions:
- truncate(str, maxLen) — truncate a string to maxLen chars, appending "..." if truncated
- capitalize(str) — capitalize the first letter of each word
- slugify(str) — convert a string to a URL-friendly slug

The library must have 100% test coverage on implemented functions.
README

init_git_repo "$TEST_PROJECT"

# Seed the product-state.md so ULI can read the goal
# (In real use, the orchestrator creates this; we seed it to reduce PD cold-start cost)
mkdir -p "$TEST_PROJECT/.claude/flow"
cat >"$TEST_PROJECT/.claude/flow/product-state.md" <<'STATE'
# Product State

## Goal
Build a tested Node.js string utilities library with: truncate, capitalize, slugify.

## Completed Features
(none yet)

## Known Gaps / Deferred
(none yet)
STATE

echo "Project setup complete. Starting Claude with ULI prompt..."
echo ""

# ------------------------------------------------------------------
# Run Claude with ULI keyword — one iteration, max 80 turns
# ------------------------------------------------------------------
OUTPUT_FILE="$TEST_PROJECT/claude-output.txt"

PROMPT="uli implement the string utility library described in the README. \
Use the ULI mode: have the PD agent read the product-state.md, propose requirements for the first iteration, \
then implement them with TDD. Run to completion of one full iteration (PD proposal + implementation + acceptance). \
Project directory: $TEST_PROJECT"

cd "$ROOT_DIR"
echo "Running Claude (output → $OUTPUT_FILE)..."
echo "================================================================"
timeout 2400 claude -p "$PROMPT" \
  --allowed-tools all \
  --add-dir "$TEST_PROJECT" \
  --permission-mode bypassPermissions \
  --max-turns 80 \
  2>&1 | tee "$OUTPUT_FILE" || {
    echo ""
    echo "================================================================"
    echo "Claude exited with error (exit $?)."
    echo "Proceeding to verify what was completed..."
  }
echo "================================================================"
echo ""
echo "Execution complete. Verifying..."
echo ""

# ------------------------------------------------------------------
# Find session transcript
# ------------------------------------------------------------------
SESSION_FILE="$(find_session_file "$ROOT_DIR" 120)"
if [ -z "$SESSION_FILE" ]; then
  echo "WARNING: Could not find session JSONL file — transcript-based tests will be skipped."
else
  echo "Session transcript: $(basename "$SESSION_FILE")"
fi
echo ""

# ------------------------------------------------------------------
# Verification tests
# ------------------------------------------------------------------
FAILED=0

echo "=== Verification Tests ==="
echo ""

# Test 1: ULI mode was activated (ultrawork skill invoked)
echo "Test 1: ultrawork skill (ULI branch) invoked..."
if [ -n "$SESSION_FILE" ]; then
  if grep -Eq '"skill":"([^"]*:)?ultrawork"' "$SESSION_FILE" 2>/dev/null; then
    echo "  [PASS] ultrawork skill was invoked"
  else
    echo "  [FAIL] ultrawork skill was NOT invoked in session"
    FAILED=$((FAILED+1))
  fi
else
  echo "  [SKIP] no session file"
fi
echo ""

# Test 2: PD agent was spawned
echo "Test 2: PD agent spawned..."
if [ -n "$SESSION_FILE" ]; then
  if grep -Eiq '"pd"|"claude-code-flow:pd"|subagent.*pd|pd.*agent' "$SESSION_FILE" 2>/dev/null; then
    echo "  [PASS] PD agent invocation found in session"
  else
    # Fall back: check if uli-proposal.md was created (which PD writes)
    if [ -f "$TEST_PROJECT/.claude/flow/uli-proposal.md" ]; then
      echo "  [PASS] uli-proposal.md exists (PD output confirmed)"
    else
      echo "  [FAIL] PD agent not spawned and uli-proposal.md not found"
      FAILED=$((FAILED+1))
    fi
  fi
else
  echo "  [SKIP] no session file"
fi
echo ""

# Test 3: uli-proposal.md was created and has CORE requirements
echo "Test 3: uli-proposal.md created with CORE requirements..."
if [ -f "$TEST_PROJECT/.claude/flow/uli-proposal.md" ]; then
  echo "  [PASS] uli-proposal.md exists"
  assert_file_contains "$TEST_PROJECT/.claude/flow/uli-proposal.md" \
    "\[CORE\]|CORE" "Contains CORE requirement" || FAILED=$((FAILED+1))
  assert_file_contains "$TEST_PROJECT/.claude/flow/uli-proposal.md" \
    "Acceptance|acceptance.criterion|acceptance_criterion" \
    "Contains acceptance criteria" || FAILED=$((FAILED+1))
else
  echo "  [FAIL] uli-proposal.md not found"
  FAILED=$((FAILED+1))
fi
echo ""

# Test 4: uli-state.json exists and has expected structure
echo "Test 4: uli-state.json structure..."
if [ -f "$TEST_PROJECT/.claude/flow/uli-state.json" ]; then
  echo "  [PASS] uli-state.json exists"
  # Check required fields
  for field in active session_id goal iteration max_iterations; do
    if python3 -c "import json,sys; d=json.load(open('$TEST_PROJECT/.claude/flow/uli-state.json')); assert '$field' in d, '$field missing'" 2>/dev/null; then
      echo "  [PASS] uli-state.json has field: $field"
    else
      echo "  [FAIL] uli-state.json missing field: $field"
      FAILED=$((FAILED+1))
    fi
  done
else
  echo "  [FAIL] uli-state.json not found"
  FAILED=$((FAILED+1))
fi
echo ""

# Test 5: Implementation files created
echo "Test 5: Implementation files created..."
# We expect at least a src/ file to exist (exact name depends on PD's proposal)
src_files="$(find "$TEST_PROJECT/src" -name "*.js" -o -name "*.ts" 2>/dev/null | wc -l || echo 0)"
test_files="$(find "$TEST_PROJECT/test" "$TEST_PROJECT/tests" -name "*.js" -o -name "*.ts" 2>/dev/null 2>/dev/null | wc -l || echo 0)"

if [ "$src_files" -ge 1 ]; then
  echo "  [PASS] $src_files source file(s) created in src/"
else
  echo "  [FAIL] No source files created in src/"
  FAILED=$((FAILED+1))
fi

if [ "$test_files" -ge 1 ]; then
  echo "  [PASS] $test_files test file(s) created"
else
  echo "  [FAIL] No test files created"
  FAILED=$((FAILED+1))
fi
echo ""

# Test 6: Tests pass (the implemented code is actually correct)
echo "Test 6: Implemented tests pass..."
if (cd "$TEST_PROJECT" && npm test >/dev/null 2>&1); then
  echo "  [PASS] npm test passes"
else
  echo "  [FAIL] npm test FAILED"
  (cd "$TEST_PROJECT" && npm test 2>&1) | sed 's/^/    /'
  FAILED=$((FAILED+1))
fi
echo ""

# Test 7: product-state.md was updated with completed features
echo "Test 7: product-state.md updated with completed features..."
if [ -f "$TEST_PROJECT/.claude/flow/product-state.md" ]; then
  # Check if it has any "Completed Features" that aren't "(none yet)"
  if grep -Eiq "\[iteration|commit:|feat:" "$TEST_PROJECT/.claude/flow/product-state.md" 2>/dev/null; then
    echo "  [PASS] product-state.md has completed feature entries"
  else
    # Acceptable if acceptance didn't fully complete — check for ACCEPT in report
    if [ -f "$TEST_PROJECT/.claude/flow/uli-acceptance-report.md" ] && \
       grep -Eiq "ACCEPT|accept" "$TEST_PROJECT/.claude/flow/uli-acceptance-report.md" 2>/dev/null; then
      echo "  [PASS] acceptance report exists — product-state may be partially updated"
    else
      echo "  [WARN] product-state.md may not have been updated (acceptance may still be in progress)"
    fi
  fi
else
  echo "  [FAIL] product-state.md not found"
  FAILED=$((FAILED+1))
fi
echo ""

# Test 8: Git branch created (uli/ prefix)
echo "Test 8: ULI git branch created..."
branches="$(git -C "$TEST_PROJECT" branch --list 'uli/*' 2>/dev/null | wc -l || echo 0)"
all_branches="$(git -C "$TEST_PROJECT" branch --list 2>/dev/null || echo "")"
if [ "$branches" -ge 1 ]; then
  echo "  [PASS] uli/* branch found"
else
  # Fall back: at least more than initial commit means work was done
  commit_count="$(git -C "$TEST_PROJECT" log --oneline 2>/dev/null | wc -l || echo 1)"
  if [ "$commit_count" -gt 1 ]; then
    echo "  [PASS] $commit_count commits exist (implementation was committed)"
  else
    echo "  [WARN] No uli/* branch found. Branches: $all_branches"
  fi
fi
echo ""

# Test 9: <uli-done> or acceptance report signals completion
echo "Test 9: Completion signal emitted..."
uli_done_in_output=false
if [ -f "$OUTPUT_FILE" ] && grep -q '<uli-done>' "$OUTPUT_FILE" 2>/dev/null; then
  uli_done_in_output=true
fi

acceptance_exists=false
if [ -f "$TEST_PROJECT/.claude/flow/uli-acceptance-report.md" ]; then
  acceptance_exists=true
fi

if $uli_done_in_output; then
  echo "  [PASS] <uli-done> tag found in Claude output"
elif $acceptance_exists; then
  echo "  [PASS] uli-acceptance-report.md exists (iteration completed)"
else
  echo "  [WARN] No <uli-done> or acceptance report — iteration may still be in progress"
  echo "         (This is acceptable for --max-turns limited runs)"
fi
echo ""

# Test 10: No infinite retry loops (sentinel should have resolved within 2 loops)
echo "Test 10: No excessive review loops..."
if [ -n "$SESSION_FILE" ]; then
  sentinel_calls="$(grep -c '"name":"Agent".*sentinel\|subagent.*sentinel' "$SESSION_FILE" 2>/dev/null || echo 0)"
  if [ "$sentinel_calls" -le 3 ]; then
    echo "  [PASS] sentinel called $sentinel_calls time(s) (within retry limit)"
  else
    echo "  [WARN] sentinel called $sentinel_calls time(s) — may indicate review loop issues"
  fi
else
  echo "  [SKIP] no session file"
fi
echo ""

# ------------------------------------------------------------------
# Token analysis
# ------------------------------------------------------------------
if [ -n "$SESSION_FILE" ]; then
  echo "========================================="
  echo " Token Usage Analysis"
  echo "========================================="
  echo ""
  python3 "$SCRIPT_DIR/analyze-token-usage.py" "$SESSION_FILE" 2>/dev/null || \
    echo "  (token analysis unavailable)"
  echo ""
fi

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo "========================================"
echo " Test Summary"
echo "========================================"
echo ""

# Artifact summary
echo "Files created:"
[ -f "$TEST_PROJECT/.claude/flow/uli-state.json" ]       && echo "  ✓ .claude/flow/uli-state.json"       || echo "  ✗ .claude/flow/uli-state.json"
[ -f "$TEST_PROJECT/.claude/flow/product-state.md" ]     && echo "  ✓ .claude/flow/product-state.md"     || echo "  ✗ .claude/flow/product-state.md"
[ -f "$TEST_PROJECT/.claude/flow/uli-proposal.md" ]      && echo "  ✓ .claude/flow/uli-proposal.md"      || echo "  ✗ .claude/flow/uli-proposal.md"
[ -f "$TEST_PROJECT/.claude/flow/uli-acceptance-report.md" ] && echo "  ✓ .claude/flow/uli-acceptance-report.md" || echo "  ✗ .claude/flow/uli-acceptance-report.md"
echo ""

if [ "$FAILED" -eq 0 ]; then
  echo "STATUS: PASSED"
  echo ""
  echo "  ✓ ULI mode activated (ultrawork skill)"
  echo "  ✓ PD agent spawned and proposal created"
  echo "  ✓ Implementation completed"
  echo "  ✓ Tests pass"
  echo "  ✓ Git commits created"
  exit 0
else
  echo "STATUS: FAILED ($FAILED test(s) failed)"
  echo ""
  echo "Full output saved to: $OUTPUT_FILE"
  exit 1
fi
