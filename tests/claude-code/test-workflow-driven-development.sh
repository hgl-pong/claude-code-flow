#!/usr/bin/env bash
# Test: workflow-driven development — behavior verification
# Uses run_claude to verify the skill describes correct behavior
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: workflow-driven development — behavior ==="
echo ""

# ── Test 1: Skill describes execution mode selection ────────────────────
echo "Test 1: Execution mode selection..."
output=$(run_claude "In the subagent-driven-development skill, how does it decide between Workflow-Driven Mode and Subagent-Driven Mode? What condition triggers each path?")

assert_contains "$output" "Workflow-Driven Mode\|workflow-driven\|Workflow.*Mode" "Mentions Workflow-Driven Mode" || true
assert_contains "$output" "Subagent-Driven Mode\|subagent-driven\|Subagent.*Mode" "Mentions Subagent-Driven Mode" || true

echo ""

# ── Test 2: Workflow-driven mode describes Controller's job ─────────────
echo "Test 2: Controller's role in workflow mode..."
output=$(run_claude "In the workflow-driven mode of subagent-driven-development, what exactly does the controller do? Describe the steps.")

assert_contains "$output" "read.*plan\|Read.*plan\|extract.*task" "Reads plan and extracts tasks" || true
assert_contains "$output" "prompt\|template" "References prompt templates" || true
assert_contains "$output" "Workflow\|script\|args" "Calls Workflow tool with script and args" || true
assert_contains "$output" "dependency.*graph\|depends_on\|topological" "Builds dependency graph" || true

echo ""

# ── Test 3: Fallback behavior ───────────────────────────────────────────
echo "Test 3: Fallback when Workflow tool unavailable..."
output=$(run_claude "What happens in subagent-driven-development when the Workflow tool is NOT available?")

assert_contains "$output" "fallback\|fall back\|not available\|Subagent-Driven Mode\|manual" "Describes fallback behavior" || true

echo ""

# ── Test 4: Pipeline structure ──────────────────────────────────────────
echo "Test 4: Pipeline structure..."
output=$(run_claude "In the workflow-driven mode of subagent-driven-development, what is the sequence of stages each task goes through? Use pipeline terms.")

assert_contains "$output" "implement\|implementer\|implementation" "Mentions implement stage" || true
assert_contains "$output" "spec.*review\|specification.*review\|spec compliance" "Mentions spec review stage" || true
assert_contains "$output" "code.*review\|code quality" "Mentions code review stage" || true
assert_contains "$output" "pipeline\|stage" "Uses pipeline language" || true

echo ""

# ── Test 5: Retry loop ──────────────────────────────────────────────────
echo "Test 5: Review retry behavior..."
output=$(run_claude "In workflow-driven development, what happens when a reviewer finds issues? How many times does it retry before giving up?")

assert_contains "$output" "retry\|loop\|fix" "Mentions retry loop" || true
assert_contains "$output" "5\|five" "Mentions 5 retries" || true

echo ""

# ── Test 6: Reviewer independence ───────────────────────────────────────
echo "Test 6: Reviewer independence..."
output=$(run_claude "What is the spec compliance reviewer's approach in workflow mode? Do they trust the implementer's report?")

assert_contains "$output" "not trust\|don't trust\|verify.*independently\|independently\|read.*actual code\|read.*code" "Reviewer verifies independently" || true

echo ""

# ── Test 7: Subagent mode unchanged ─────────────────────────────────────
echo "Test 7: Subagent-driven mode still documented..."
output=$(run_claude "In the subagent-driven mode of subagent-driven-development, does the controller manually dispatch subagents and manage review chains?")

assert_contains "$output" "dispatch\|调度\|spawn.*implementer\|Spec.*Review\|spec reviewer\|规范审查" "Controller dispatches manually" || true
assert_contains "$output" "spec.*code\|spec.*before.*code\|规范.*代码\|spec reviewer.*code quality\|in order\|然后\|then.*code\|✅\|1\..*spec\|implementer.*spec.*code" "Spec before code quality order" || true

echo ""

# ── Test 8: Pre-flight checklist ────────────────────────────────────────
echo "Test 8: Pre-flight checklist..."
output=$(run_claude "What does the workflow-driven mode say about checking hooks before launching a workflow?")

assert_contains "$output" "hook\|PreToolUse\|interfere" "Mentions hook checking" || true
assert_contains "$output" "allowlist\|allow list\|白名单\|permission\|shell.*command\|命令.*权限\|pre.approve\|tool.*allow" "Mentions shell command allowlist" || true

echo ""

# ── Test 9: Existing content preserved ──────────────────────────────────
echo "Test 9: Existing content preserved..."
output=$(run_claude "What is the core principle of subagent-driven-development?")

assert_contains "$output" "fresh subagent\|two-stage\|spec.*quality" "Core principle preserved" || true

output2=$(run_claude "What does subagent-driven-development say about reading the plan file?")
assert_contains "$output2" "once\|once.*beginning\|one time\|single time" "Plan read once rule preserved" || true

echo ""

report_failures
exit $?
