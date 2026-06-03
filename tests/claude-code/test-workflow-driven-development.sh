#!/usr/bin/env bash
# Test: workflow-driven development — behavior verification
# Uses run_claude to verify the skill describes correct behavior
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: workflow-driven development — behavior ==="
echo ""

# ── Test 1: Skill recognizes the correct name ──────────────────────────
echo "Test 1: Skill name..."
output=$(run_claude "What is the workflow-driven-development skill? Describe what it does in one sentence.")

assert_contains "$output" "workflow-driven-development\|Workflow-driven\|workflow driven\|Workflow-Driven" "Skill is recognized by name" || true
assert_contains "$output" "Dynamic Workflows\|Workflow" "References Dynamic Workflows" || true

echo ""

# ── Test 2: Four-step process ──────────────────────────────────────────
echo "Test 2: Four-step process..."
output=$(run_claude "In the workflow-driven-development skill, what are the four steps the controller follows? List them in order.")

assert_contains "$output" "prepare.*context\|Prepare.*[Cc]ontext\|read.*plan\|extract.*task" "Step 1: Prepare context" || true
assert_contains "$output" "build.*args\|Build.*[Aa]rgs\|construct.*args" "Step 2: Build args" || true
assert_contains "$output" "[Ll]aunch\|Workflow(" "Step 3: Launch" || true
assert_contains "$output" "handle.*result\|Handle.*[Rr]esult\|monitor.*result" "Step 4: Handle results" || true

echo ""

# ── Test 3: Pipeline stages ────────────────────────────────────────────
echo "Test 3: Pipeline stages..."
output=$(run_claude "In workflow-driven-development, what stages does each task go through? What order?")

assert_contains "$output" "[Ii]mplement" "Mentions implement stage" || true
assert_contains "$output" "spec.*review\|[Ss]pec.*compliance" "Spec review comes before code review" || true
assert_contains "$output" "code.*review\|[Cc]ode.*quality" "Mentions code review stage" || true

echo ""

# ── Test 4: Retry behavior ─────────────────────────────────────────────
echo "Test 4: Retry behavior..."
output=$(run_claude "In workflow-driven-development, what happens when a reviewer finds issues? How many retries are allowed?")

assert_contains "$output" "retry\|loop\|fix.*and.*re-review" "Mentions retry loop" || true
assert_contains "$output" "5\|five" "Mentions max retries" || true

echo ""

# ── Test 5: Reviewer independence ──────────────────────────────────────
echo "Test 5: Reviewer independence..."
output=$(run_claude "In workflow-driven-development, does the spec compliance reviewer trust the implementer's report?")

assert_contains "$output" "not trust\|don.*trust\|verify.*independently\|independently\|read.*code" "Reviewer verifies independently" || true
assert_contains "$output" "suspiciously\|incomplete\|optimistic" "Reviewer is skeptical" || true

echo ""

# ── Test 6: Results structure ──────────────────────────────────────────
echo "Test 6: Results structure..."
output=$(run_claude "What does the workflow return in workflow-driven-development? Describe results.completed and results.blocked.")

assert_contains "$output" "completed\|results.completed" "Mentions results.completed" || true
assert_contains "$output" "blocked\|results.blocked" "Mentions results.blocked" || true
assert_contains "$output" "final_review\|cross-task" "Mentions final review" || true

echo ""

# ── Test 7: Blocked tasks handling ─────────────────────────────────────
echo "Test 7: Blocked tasks..."
output=$(run_claude "In workflow-driven-development, how should the controller handle tasks that appear in results.blocked?")

assert_contains "$output" "re-dispatch\|better model\|more capable model" "Re-dispatch with better model" || true
assert_contains "$output" "split\|smaller\|break.*down" "Split into smaller tasks" || true
assert_contains "$output" "escalate\|human partner\|plan.*wrong" "Escalate for plan-level issues" || true
assert_contains "$output" "same.*model\|same.*instruction" "Do NOT re-dispatch unchanged" || true

echo ""

# ── Test 8: Model selection ────────────────────────────────────────────
echo "Test 8: Model selection..."
output=$(run_claude "What models are available for workflow agents in workflow-driven-development? List forge, oracle, prism, and artist.")

assert_contains "$output" "forge\|Forge" "Mentions forge" || true
assert_contains "$output" "oracle\|Oracle" "Mentions oracle" || true
assert_contains "$output" "prism\|Prism" "Mentions prism" || true
assert_contains "$output" "artist\|Artist" "Mentions artist" || true

echo ""

# ── Test 9: Red Flags ──────────────────────────────────────────────────
echo "Test 9: Red Flags..."
output=$(run_claude "List the 'Never' rules from the workflow-driven-development red flags section.")

assert_contains "$output" "plan.*file\|read.*plan\|plan file" "Must read plan file" || true
assert_contains "$output" "main\|master" "No main/master without consent" || true
assert_contains "$output" "blocked\|ignore" "Don't ignore blocked tasks" || true
assert_contains "$output" "interrupt\|cancel" "Don't interrupt workflow" || true

echo ""

# ── Test 10: Integration references ────────────────────────────────────
echo "Test 10: Integration..."
output=$(run_claude "What skills does workflow-driven-development require before use?")

assert_contains "$output" "using-git-worktrees\|git.*worktree" "Requires git worktrees skill" || true
assert_contains "$output" "writing-plans\|writing.*plan" "Requires writing-plans skill" || true
assert_contains "$output" "finishing.*branch\|finishing-a-development-branch" "Requires finishing skill" || true

echo ""

report_failures
exit $?
