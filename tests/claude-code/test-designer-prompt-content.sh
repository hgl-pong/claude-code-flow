#!/usr/bin/env bash
# Test: designer-prompt.md content verification
# Static checks — no Claude Code invocation needed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

PROMPT_FILE="$SCRIPT_DIR/../../skills/subagent-driven-development/designer-prompt.md"

echo "=== Test: designer-prompt.md content ==="
echo ""

if [ ! -f "$PROMPT_FILE" ]; then
    echo "  [FAIL] Prompt file not found: $PROMPT_FILE"
    exit 1
fi

PROMPT_CONTENT=$(cat "$PROMPT_FILE")

# Test 1: Source provenance in Synthesize step
echo "Test 1: Source provenance in synthesize..."
assert_contains "$PROMPT_CONTENT" "URLs and access dates" "URLs and access dates in synthesize" || true
assert_contains "$PROMPT_CONTENT" "Cross-reference table" "Cross-reference table mentioned" || true

# Test 2: Quality checklist has URL requirement
echo ""
echo "Test 2: Quality checklist..."
assert_contains "$PROMPT_CONTENT" "URLs and access dates" "Checklist: URLs and dates" || true
assert_contains "$PROMPT_CONTENT" "web sources cited" "Checklist: web sources" || true

# Test 3: DESIGN.md Research Summary has traceability
echo ""
echo "Test 3: DESIGN.md traceability..."
assert_contains "$PROMPT_CONTENT" "traceable to its source" "DESIGN.md traceability requirement" || true

# Test 4: Web tools still present (Phase 1 unchanged)
echo ""
echo "Test 4: Web tools still present..."
assert_contains "$PROMPT_CONTENT" "WebSearch" "WebSearch in designer" || true
assert_contains "$PROMPT_CONTENT" "WebFetch" "WebFetch in designer" || true

# Test 5: Phase 1 structure preserved
echo ""
echo "Test 5: Phase 1 structure..."
assert_contains "$PROMPT_CONTENT" "Competitive Analysis" "Competitive analysis step" || true
assert_contains "$PROMPT_CONTENT" "Design Pattern Research" "Design pattern step" || true
assert_contains "$PROMPT_CONTENT" "Domain-Appropriate References" "Domain references step" || true
assert_contains "$PROMPT_CONTENT" "Synthesize" "Synthesize step" || true

echo ""
report_failures
exit $?
