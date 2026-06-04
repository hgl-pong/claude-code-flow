#!/usr/bin/env bash
# E2E: Test-Driven Development Skill
# Verifies the TDD skill enforces RED-GREEN-REFACTOR cycle.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Test-Driven Development Skill"
echo "========================================"
echo ""

# ── Test 1: Skill recognition ──
echo "Test 1: Skill name and RED-GREEN-REFACTOR..."
output=$(run_claude "What is the claude-code-flow:test-driven-development skill? Describe the RED-GREEN-REFACTOR cycle." 120)

assert_contains "$output" "test-driven-development\|TDD\|Test-Driven" \
    "Skill is recognized by name" || true
assert_contains "$output" "RED.*GREEN.*REFACTOR\|red.*green.*refactor" \
    "Mentions RED-GREEN-REFACTOR cycle" || true

echo ""

# ── Test 2: Write test first ──
echo "Test 2: Test-first mandate..."
output=$(run_claude "In the test-driven-development skill, in what order should tests and code be written?" 120)

assert_contains "$output" "test.*first\|first.*test\|before.*code\|write.*test.*before\|[Ff]ailing.*[Tt]est.*[Ff]irst\|NO.*PRODUCTION.*WITHOUT\|先写.*测试\|测试.*在先" \
    "Tests must be written before code" || true

echo ""

# ── Test 3: Watch test fail ──
echo "Test 3: RED phase..."
output=$(run_claude "In the test-driven-development skill, after writing a failing test, what MUST you do before writing implementation code?" 120)

assert_contains "$output" "watch.*fail\|see.*fail\|verify.*fail\|run.*test.*fail\|confirm.*fail" \
    "Must watch/verify test fails before implementing" || true

echo ""

# ── Test 4: Minimal implementation ──
echo "Test 4: GREEN phase..."
output=$(run_claude "In the test-driven-development skill, how much code should be written during the GREEN phase?" 120)

assert_contains "$output" "minimal\|minimally\|minimize\|simplest\|just.*enough\|bare.*minimum" \
    "GREEN phase should write minimal code" || true

echo ""

# ── Test 5: Anti-patterns reference ──
echo "Test 5: Testing anti-patterns..."
output=$(run_claude "What testing anti-patterns are documented in the test-driven-development skill?" 120)

assert_contains "$output" "anti-pattern\|mock\|too.*many\|dependency" \
    "Mentions testing anti-patterns" || true

echo ""

# ── Test 6: No code before tests ──
echo "Test 6: Code-before-test prohibition..."
output=$(run_claude "In the test-driven-development skill, if I write implementation code before a failing test, what should happen?" 120)

assert_contains "$output" "[Dd]elete\|[Rr]emove\|[Dd]iscard\|throw.*away\|[Rr]evert\|start.*over\|重新\|删除" \
    "Code written before tests should be deleted" || true

echo ""

report_failures
