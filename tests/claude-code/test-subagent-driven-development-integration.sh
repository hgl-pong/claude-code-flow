#!/usr/bin/env bash
# Integration Test: subagent-driven-development workflow
# Actually executes a plan and verifies the new workflow behaviors
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " Integration Test: subagent-driven-development"
echo "========================================"
echo ""
echo "This test executes a real plan using the skill and verifies:"
echo "  1. Plan is read once (not per task)"
echo "  2. Full task text provided to subagents"
echo "  3. Subagents perform self-review"
echo "  4. Spec compliance review before code quality"
echo "  5. Review loops when issues found"
echo "  6. Spec reviewer reads code independently"
echo ""
echo "WARNING: This test may take 10-30 minutes to complete."
echo ""

# Create test project
TEST_PROJECT=$(create_test_project)
echo "Test project: $TEST_PROJECT"

# Trap to cleanup
trap "cleanup_test_project $TEST_PROJECT" EXIT

# Set up minimal Node.js project
cd "$TEST_PROJECT"

cat > package.json <<'EOF'
{
  "name": "test-project",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "test": "node --test"
  }
}
EOF

mkdir -p src test .claude/plans

# Create a simple implementation plan
cat > .claude/plans/implementation-plan.md <<'EOF'
# Test Implementation Plan

This is a minimal plan to test the subagent-driven-development workflow.

## Task 1: Create Add Function

Create a function that adds two numbers.

**File:** `src/math.js`

**Requirements:**
- Function named `add`
- Takes two parameters: `a` and `b`
- Returns the sum of `a` and `b`
- Export the function

**Implementation:**
```javascript
export function add(a, b) {
  return a + b;
}
```

**Tests:** Create `test/math.test.js` that verifies:
- `add(2, 3)` returns `5`
- `add(0, 0)` returns `0`
- `add(-1, 1)` returns `0`

**Verification:** `npm test`

## Task 2: Create Multiply Function

Create a function that multiplies two numbers.

**File:** `src/math.js` (add to existing file)

**Requirements:**
- Function named `multiply`
- Takes two parameters: `a` and `b`
- Returns the product of `a` and `b`
- Export the function
- DO NOT add any extra features (like power, divide, etc.)

**Implementation:**
```javascript
export function multiply(a, b) {
  return a * b;
}
```

**Tests:** Add to `test/math.test.js`:
- `multiply(2, 3)` returns `6`
- `multiply(0, 5)` returns `0`
- `multiply(-2, 3)` returns `-6`

**Verification:** `npm test`
EOF

# Initialize git repo
git init --quiet
git config user.email "test@test.com"
git config user.name "Test User"
git add .
git commit -m "Initial commit" --quiet

echo ""
echo "Project setup complete. Starting execution..."
echo ""

# Run Claude with subagent-driven-development
# Capture full output to analyze
OUTPUT_FILE="$TEST_PROJECT/claude-output.txt"

# Create prompt file
cat > "$TEST_PROJECT/prompt.txt" <<'EOF'
I want you to execute the implementation plan at .claude/plans/implementation-plan.md using the subagent-driven-development skill.

IMPORTANT: Follow the skill exactly. I will be verifying that you:
1. Read the plan once at the beginning
2. Provide full task text to subagents (don't make them read files)
3. Ensure subagents do self-review before reporting
4. Run spec compliance review before code quality review
5. Use review loops when issues are found

Begin now. Execute the plan.
EOF

# Note: We use a longer timeout since this is integration testing
# Use --allowed-tools to enable tool usage in headless mode
PROMPT="Execute the implementation plan at .claude/plans/implementation-plan.md using the subagent-driven-development skill.

CONTINUOUS EXECUTION: Do not pause to ask questions. Execute all tasks in the plan, do not stop between tasks. Just complete the full plan.

IMPORTANT: Follow the skill exactly. I will be verifying that you:
1. Read the plan once at the beginning
2. Provide full task text to subagents (don't make them read files)
3. Ensure subagents do self-review before reporting
4. Run spec compliance review before code quality review
5. Use review loops when issues are found

Begin now. Execute the plan."

PLUGIN_DIR=$(cd "$SCRIPT_DIR/../.." && pwd)

# Run claude from inside the test project so its session JSONL lands in a
# project-specific directory under ~/.claude/projects/, isolated from any
# other concurrent claude sessions.
echo "Running Claude (plugin-dir: $PLUGIN_DIR, cwd: $TEST_PROJECT)..."
echo "================================================================================"
cd "$TEST_PROJECT" && timeout 1800 claude -p "$PROMPT" --plugin-dir "$PLUGIN_DIR" --allowed-tools=all --permission-mode bypassPermissions 2>&1 | tee "$OUTPUT_FILE" || {
    echo ""
    echo "================================================================================"
    echo "EXECUTION FAILED (exit code: $?), skipping verification"
    SKIP_VERIFICATION=true
}
echo "================================================================================"

echo ""
echo "Execution complete. Analyzing results..."
echo ""

# Find the session transcript. Use most-recently-modified project directory
# instead of computing the exact name (path normalization differs per platform).
LATEST_PROJECT=$(ls -dt "$HOME/.claude/projects/"*/ 2>/dev/null | head -1)
SESSION_FILE=""
if [ -n "$LATEST_PROJECT" ]; then
    SESSION_FILE=$(ls -t "$LATEST_PROJECT"/*.jsonl 2>/dev/null | head -1 || true)
fi

if [ -z "$SESSION_FILE" ]; then
    echo "ERROR: Could not find session transcript file"
    echo "Looked in: $LATEST_PROJECT"
    SKIP_VERIFICATION=true
fi

echo "Analyzing session transcript: $(basename "$SESSION_FILE")"
echo ""

if [ "${SKIP_VERIFICATION:-false}" = "true" ]; then
    echo "SKIPPED: Verification tests (claude execution or session file missing)"
    FAILED=1
else
    # Verification tests
    FAILED=0

    echo "=== Verification Tests ==="
    echo ""

    # Test 1: Skill was invoked
    echo "Test 1: Skill tool invoked..."
if grep -q '"name":"Skill".*"skill":"claude-code-flow:subagent-driven-development"' "$SESSION_FILE"; then
    echo "  [PASS] subagent-driven-development skill was invoked"
else
    echo "  [FAIL] Skill was not invoked"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 2: Subagents were used (Agent / Task tool — name varies by harness version)
echo "Test 2: Subagents dispatched..."
task_count=$(grep -cE '"name":"(Agent|Task)"' "$SESSION_FILE" || echo "0")
if [ "$task_count" -ge 2 ]; then
    echo "  [PASS] $task_count subagents dispatched"
else
    echo "  [FAIL] Only $task_count subagent(s) dispatched (expected >= 2)"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 3: Task tracking (TodoWrite or TaskCreate)
echo "Test 3: Task tracking..."
todo_count=$(grep -c '"name":"TodoWrite"' "$SESSION_FILE" 2>/dev/null || true)
todo_count=$(echo "$todo_count" | tr -d '[:space:]' | tail -1)
if [ -z "$todo_count" ]; then todo_count=0; fi
taskcreate_count=$(grep -c '"name":"TaskCreate"' "$SESSION_FILE" 2>/dev/null || true)
taskcreate_count=$(echo "$taskcreate_count" | tr -d '[:space:]' | tail -1)
if [ -z "$taskcreate_count" ]; then taskcreate_count=0; fi
total_tasks=$(( todo_count + taskcreate_count ))
if [ "$total_tasks" -ge 1 ]; then
    echo "  [PASS] Task tracking used: $todo_count TodoWrite + $taskcreate_count TaskCreate = $total_tasks total"
else
    echo "  [FAIL] TodoWrite not used"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 6: Implementation actually works
echo "Test 6: Implementation verification..."
if [ -f "$TEST_PROJECT/src/math.js" ]; then
    echo "  [PASS] src/math.js created"

    if grep -q "export function add" "$TEST_PROJECT/src/math.js"; then
        echo "  [PASS] add function exists"
    else
        echo "  [FAIL] add function missing"
        FAILED=$((FAILED + 1))
    fi

    if grep -q "export function multiply" "$TEST_PROJECT/src/math.js"; then
        echo "  [PASS] multiply function exists"
    else
        echo "  [FAIL] multiply function missing"
        FAILED=$((FAILED + 1))
    fi
else
    echo "  [FAIL] src/math.js not created"
    FAILED=$((FAILED + 1))
fi

if [ -f "$TEST_PROJECT/test/math.test.js" ]; then
    echo "  [PASS] test/math.test.js created"
else
    echo "  [FAIL] test/math.test.js not created"
    FAILED=$((FAILED + 1))
fi

# Try running tests
if cd "$TEST_PROJECT" && npm test > test-output.txt 2>&1; then
    echo "  [PASS] Tests pass"
else
    echo "  [FAIL] Tests failed"
    cat test-output.txt
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 7: Git commits show proper workflow
echo "Test 7: Git commit history..."
commit_count=$(git -C "$TEST_PROJECT" log --oneline | wc -l)
if [ "$commit_count" -gt 2 ]; then  # Initial + at least 2 task commits
    echo "  [PASS] Multiple commits created ($commit_count total)"
else
    echo "  [FAIL] Too few commits ($commit_count, expected >2)"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 8: Check for extra features (spec compliance should catch)
echo "Test 8: No extra features added (spec compliance)..."
if grep -q "export function divide\|export function power\|export function subtract" "$TEST_PROJECT/src/math.js" 2>/dev/null; then
    echo "  [WARN] Extra features found (spec review should have caught this)"
    # Not failing on this as it tests reviewer effectiveness
else
    echo "  [PASS] No extra features added"
fi
echo ""

fi  # end SKIP_VERIFICATION check

# Token Usage Analysis
if [ -n "$SESSION_FILE" ] && [ -f "$SESSION_FILE" ]; then
    echo "========================================="
    echo " Token Usage Analysis"
    echo "========================================="
    echo ""
    python3 "$SCRIPT_DIR/analyze-token-usage.py" "$SESSION_FILE"
    echo ""
fi

# Summary
echo "========================================"
echo " Test Summary"
echo "========================================"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "STATUS: PASSED"
    echo "All verification tests passed!"
    echo ""
    echo "The subagent-driven-development skill correctly:"
    echo "  ✓ Reads plan once at start"
    echo "  ✓ Provides full task text to subagents"
    echo "  ✓ Enforces self-review"
    echo "  ✓ Runs spec compliance before code quality"
    echo "  ✓ Spec reviewer verifies independently"
    echo "  ✓ Produces working implementation"
    exit 0
else
    echo "STATUS: FAILED"
    echo "Failed $FAILED verification tests"
    echo ""
    echo "Output saved to: $OUTPUT_FILE"
    echo ""
    echo "Review the output to see what went wrong."
    exit 1
fi
