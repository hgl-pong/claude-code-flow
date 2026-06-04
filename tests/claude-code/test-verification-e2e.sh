#!/usr/bin/env bash
# E2E: Verification Before Completion Skill
# Verifies the verification skill ensures work is properly validated before declaring done.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Verification Before Completion"
echo "========================================"
echo ""

# ── Test 1: Skill recognition ──
echo "Test 1: Skill name and purpose..."
output=$(run_claude "What is the claude-code-flow:verification-before-completion skill? What does it do?" 120)

assert_contains "$output" "verification-before-completion\|Verification Before Completion\|verification" \
    "Skill is recognized by name" || true
assert_contains "$output" "verify\|test.*pass\|check\|validate\|confirm" \
    "Skill purpose includes verification/validation" || true

echo ""

# ── Test 2: What to verify ──
echo "Test 2: Verification checklist..."
output=$(run_claude "In the verification-before-completion skill, what specific things should be verified before declaring completion?" 120)

assert_contains "$output" "test.*pass\|tests.*running\|test.*suite" \
    "Mentions tests passing" || true

echo ""

# ── Test 3: Evidence requirement ──
echo "Test 3: Evidence and proof..."
output=$(run_claude "In the verification-before-completion skill, is it enough to just claim something works? What evidence is needed?" 120)

assert_contains "$output" "evidence\|proof\|demonstrate\|show\|run\|output" \
    "Requires evidence/proof, not just claims" || true

echo ""

report_failures
