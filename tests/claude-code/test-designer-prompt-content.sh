#!/usr/bin/env bash
# Test: designer-prompt.md content verification
# Static checks — no Claude Code invocation needed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

PROMPT_FILE="$SCRIPT_DIR/../../skills/auto-mode/prompts/designer-prompt.md"
FORMAT_FILE="$SCRIPT_DIR/../../skills/auto-mode/prompts/design-md-format.md"

echo "=== Test: designer-prompt.md content ==="
echo ""

if [ ! -f "$PROMPT_FILE" ]; then
    echo "  [FAIL] Prompt file not found: $PROMPT_FILE"
    exit 1
fi

if [ ! -f "$FORMAT_FILE" ]; then
    echo "  [FAIL] Format file not found: $FORMAT_FILE"
    exit 1
fi

PROMPT_CONTENT=$(cat "$PROMPT_FILE")
FORMAT_CONTENT=$(cat "$FORMAT_FILE")

# Test 1: Source provenance in Synthesize step
echo "Test 1: Source provenance in synthesize..."
assert_contains "$PROMPT_CONTENT" "URLs and access dates" "URLs and access dates in synthesize" || true
assert_contains "$PROMPT_CONTENT" "Cross-reference table" "Cross-reference table mentioned" || true

# Test 2: Format reference has source-backed research requirements
echo ""
echo "Test 2: Format reference source requirements..."
assert_contains "$FORMAT_CONTENT" "URLs/access dates" "Format: URLs and dates" || true
assert_contains "$FORMAT_CONTENT" "source-backed conclusions" "Format: source-backed conclusions" || true

# Test 3: DESIGN.md Research Summary has traceability
echo ""
echo "Test 3: DESIGN.md traceability..."
assert_contains "$FORMAT_CONTENT" "Every major design decision below must cite" "DESIGN.md traceability requirement" || true

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

# Test 6: Designer prompt references extracted format
echo ""
echo "Test 6: Format reference wired..."
assert_contains "$PROMPT_CONTENT" "design-md-format.md" "Prompt references format file" || true
assert_contains "$FORMAT_CONTENT" "Primitive Tokens" "Format: primitive tokens" || true
assert_contains "$FORMAT_CONTENT" "Semantic Tokens" "Format: semantic tokens" || true
assert_contains "$FORMAT_CONTENT" "Component Tokens" "Format: component tokens" || true
assert_contains "$FORMAT_CONTENT" "Theme Groups" "Format: theme groups" || true
assert_contains "$FORMAT_CONTENT" "Variant × State Matrix" "Format: variant-state matrix" || true
assert_contains "$FORMAT_CONTENT" "44px touch targets" "Format: touch target minimum" || true

echo ""
report_failures
exit $?

