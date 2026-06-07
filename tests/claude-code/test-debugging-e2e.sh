#!/usr/bin/env bash
# E2E: Systematic Debugging Skill
# Verifies the debugging skill provides the 4-phase root cause process.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Systematic Debugging Skill"
echo "========================================"
echo ""

# ── Test 1: Skill recognition ──
echo "Test 1: Skill name and process..."
output=$(run_claude "What is the claude-code-flow:systematic-debugging skill? Describe its debugging process phases." 120)

assert_contains "$output" "systematic-debugging\|Systematic Debugging\|debugging" \
    "Skill is recognized by name" || true
assert_contains "$output" "phase\|step\|process" \
    "Mentions structured debugging process" || true

echo ""

# ── Test 2: Root cause focus ──
echo "Test 2: Root cause vs symptoms..."
output=$(run_claude "In the systematic-debugging skill, should you fix symptoms or find root causes?" 120)

assert_contains "$output" "root cause\|root.*cause\|underlying\|source" \
    "Emphasizes finding root causes" || true
assert_contains "$output" "symptom\|surface\|band.*aid\|patch" \
    "Warns against just fixing symptoms" || true

echo ""

# ── Test 3: Hypothesis testing ──
echo "Test 3: Hypothesis-driven approach..."
output=$(run_claude "In the systematic-debugging skill, how should you form and test hypotheses?" 120)

assert_contains "$output" "hypothesis\|hypothesi[sz]e\|theory\|predict" \
    "Mentions hypothesis formation/testing" || true

echo ""

# ── Test 4: Verification after fix ──
echo "Test 4: Post-fix verification..."
output=$(run_claude "In the systematic-debugging skill, after applying a fix, what must be verified?" 120)

assert_contains "$output" "verify\|confirm\|test.*pass\|reproduc\|check" \
    "Must verify fix actually works" || true
assert_contains "$output" "regression\|new.*bug\|break.*other\|side.*effect" \
    "Must check for regressions" || true

echo ""

report_failures
