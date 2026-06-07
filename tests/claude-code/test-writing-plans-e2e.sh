#!/usr/bin/env bash
# E2E: Writing Plans Skill
# Verifies the writing-plans skill creates correct implementation plans.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Writing Plans Skill"
echo "========================================"
echo ""

# ── Test 1: Skill recognition ──
echo "Test 1: Skill name and purpose..."
output=$(run_claude "What is the claude-code-flow:writing-plans skill? What does it do?" 120)

assert_contains "$output" "writing-plans\|Writing Plans\|writing.*plan" \
    "Skill is recognized by name" || true
assert_contains "$output" "task\|break.*down\|decompose\|implementation.*plan" \
    "Skill purpose includes breaking work into tasks" || true

echo ""

# ── Test 2: Task characteristics ──
echo "Test 2: Task granularity..."
output=$(run_claude "In the writing-plans skill, how long should each task take? What information must each task include?" 120)

assert_contains "$output" "2-5.*minute\|2.*5.*minutes\|few.*minutes\|small" \
    "Tasks should be 2-5 minutes" || true
assert_contains "$output" "file.*path\|file.*name\|verification\|test" \
    "Tasks must include file paths and verification" || true

echo ""

# ── Test 3: Dependency handling ──
echo "Test 3: Task dependencies..."
output=$(run_claude "In the writing-plans skill, how are task dependencies managed? How do you decide what tasks can run in parallel?" 120)

assert_contains "$output" "depend\|dependency\|depends_on\|block" \
    "Mentions task dependencies" || true
assert_contains "$output" "parallel\|concurrent\|independent" \
    "Mentions parallel execution for independent tasks" || true

echo ""

# ── Test 4: Plan reviewer integration ──
echo "Test 4: Plan reviewer..."
output=$(run_claude "In the writing-plans skill, is there a review step for the plan? What reviewer is used?" 120)

assert_contains "$output" "review.*plan\|plan.*review\|reviewer" \
    "Mentions plan review step" || true

echo ""

# ── Test 5: Specification dependency ──
echo "Test 5: Spec prerequisite..."
output=$(run_claude "In the writing-plans skill, what must exist before writing a plan?" 120)

assert_contains "$output" "spec\|design\|requirement.*doc\|brainstorming" \
    "Requires spec/design document before planning" || true

echo ""

report_failures
