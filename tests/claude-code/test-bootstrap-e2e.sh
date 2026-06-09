#!/usr/bin/env bash
# E2E: Bootstrap Verification
# Verifies the using-claude-code-flow skill loads and triggers correctly.
# Tests that Claude recognizes the bootstrap skill and follows its instructions.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Bootstrap Skill Verification"
echo "========================================"
echo ""

# ── Test 1: Bootstrap skill is recognized by Claude ──
echo "Test 1: Bootstrap skill recognition..."
output=$(run_claude "What is the claude-code-flow:using-claude-code-flow skill? What is its purpose?" 120)

assert_contains "$output" "using-claude-code-flow\|Using Claude Code Flow\|bootstrap" \
    "Bootstrap skill is recognized" || true

echo ""

# ── Test 2: Bootstrap instructs to check for skills ──
echo "Test 2: Skill-check instruction..."
output=$(run_claude "According to the using-claude-code-flow skill, when should you invoke other skills?" 120)

assert_contains "$output" "before\|first\|before any response\|before.*action" \
    "Skills should be checked before any response" || true

echo ""

# ── Test 3: Red Flags table is intact ──
echo "Test 3: Red Flags completeness..."
output=$(run_claude "List the Red Flags from the using-claude-code-flow skill. What rationalizations should you avoid?" 120)

# Check key anti-rationalization phrases from the skill
assert_contains "$output" "simple question\|just a simple" \
    "Mentions 'simple question' rationalization" || true
assert_contains "$output" "explore.*codebase\|Let me explore" \
    "Mentions 'explore codebase' rationalization" || true
assert_contains "$output" "overkill" \
    "Mentions 'overkill' rationalization" || true

echo ""

# ── Test 4: Skill priority order ──
echo "Test 4: Skill priority..."

# The bootstrap says orchestration skills first, then domain/tool skills.
output=$(run_claude "According to the using-claude-code-flow skill, what is the skill priority order? Which skills should be checked first?" 120)

assert_contains "$output" "orchestration\|auto-mode\|semi-auto\|debugging" \
    "Orchestration skills have priority" || true
assert_contains "$output" "domain/tool\|domain.*second\|tool.*second" \
    "Domain/tool skills come second" || true

echo ""

# ── Test 5: Skill tool instruction ──
echo "Test 5: Skill tool usage..."
output=$(run_claude "According to the using-claude-code-flow skill, how should skills be invoked? What tool should be used?" 120)

assert_contains "$output" "Skill\|skill tool\|invoke.*skill" \
    "Mentions Skill tool for invocation" || true

echo ""

report_failures
