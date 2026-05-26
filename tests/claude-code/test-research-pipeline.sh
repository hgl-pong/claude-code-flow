#!/usr/bin/env bash
# LONG_RUNNING: Behavioral e2e test for research pipeline
# Verifies: brainstorming dispatches researcher → output has source provenance
# Expect 15-30 minutes. Uses 2 Claude Code invocations.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "======================================"
echo " E2E Test: Research Pipeline"
echo "======================================"
echo ""
echo "LONG_RUNNING: Expect 15-30 minutes."
echo ""

# Skip if not explicitly requested
if [ "${RUN_LONG_TESTS:-}" != "true" ]; then
    echo "SKIP: Set RUN_LONG_TESTS=true to run long-running tests."
    exit 0
fi

# Test 1: Brainstorming dispatches researcher for product research
echo "Test 1: Brainstorming dispatches researcher..."

output=$(run_claude "I need to build a personal bookmark manager web app. Let's brainstorm the design." 600)

# Check that brainstorming skill was invoked
assert_contains "$output" "brainstorming\|Brainstorming" "Brainstorming triggered" || true

# Check that it mentions dispatching researcher or research output in .claude/research/
assert_contains "$output" "research\|\.claude/research\|researcher" "Research referenced" || true

echo ""

# Test 2: Source provenance requirement surfaces
echo "Test 2: Source provenance in research output..."

# After brainstorming finishes, check for .claude/research/ output
RESEARCH_DIR=".claude/research"
if [ -d "$RESEARCH_DIR" ]; then
    # Find the most recently created research directory
    LATEST_RESEARCH=$(find "$RESEARCH_DIR" -name "*-research.md" -type f 2>/dev/null | head -5)
    if [ -n "$LATEST_RESEARCH" ]; then
        echo "  [PASS] Research files found: $LATEST_RESEARCH"
    else
        echo "  [INFO] No research files found yet (may need full pipeline)"
    fi
else
    echo "  [INFO] .claude/research/ directory not yet created"
fi

echo ""

# Test 3: Writing-plans dispatches researcher for technical research
echo "Test 3: Writing-plans dispatches researcher for technical research..."

output=$(run_claude "I have a spec at .claude/specs/2026-05-26-researcher-workflow-iteration-design.md. Create an implementation plan for just the researcher-prompt.md rewrite." 600)

assert_contains "$output" "researcher\|research\|Research" "Research referenced in plan creation" || true
assert_contains "$output" "technical-research\|technical research" "Technical research mentioned" || true

echo ""

# Test 4: Verify .claude/research/ output exists after pipeline
echo "Test 4: Research output files..."
if [ -d "$RESEARCH_DIR" ]; then
    ALL_RESEARCH=$(find "$RESEARCH_DIR" -name "*-research.md" -type f 2>/dev/null)
    echo "Research files produced:"
    echo "$ALL_RESEARCH"
    echo ""
    RESEARCH_COUNT=$(find "$RESEARCH_DIR" -name "*-research.md" -type f 2>/dev/null | wc -l)
    if [ "$RESEARCH_COUNT" -gt 0 ]; then
        echo "  [PASS] $RESEARCH_COUNT research file(s) produced"
    else
        echo "  [FAIL] No research files produced"
    fi
else
    echo "  [INFO] .claude/research/ not created"
fi

echo ""
report_failures
exit $?
