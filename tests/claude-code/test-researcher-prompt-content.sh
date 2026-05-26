#!/usr/bin/env bash
# Test: researcher-prompt.md content verification
# Static checks — no Claude Code invocation needed
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

PROMPT_FILE="$SCRIPT_DIR/../../skills/subagent-driven-development/researcher-prompt.md"

echo "=== Test: researcher-prompt.md content ==="
echo ""

if [ ! -f "$PROMPT_FILE" ]; then
    echo "  [FAIL] Prompt file not found: $PROMPT_FILE"
    exit 1
fi

PROMPT_CONTENT=$(cat "$PROMPT_FILE")

# Test 1: Local tools section exists
echo "Test 1: Local tools..."
assert_contains "$PROMPT_CONTENT" "Local Codebase Tools" "Local tools section" || true
assert_contains "$PROMPT_CONTENT" "Glob" "Glob tool mentioned" || true
assert_contains "$PROMPT_CONTENT" "Grep" "Grep tool mentioned" || true
assert_contains "$PROMPT_CONTENT" "CodeGraph" "CodeGraph mentioned" || true

# Test 2: Web tools section exists
echo ""
echo "Test 2: Web tools..."
assert_contains "$PROMPT_CONTENT" "Web Tools" "Web tools section" || true
assert_contains "$PROMPT_CONTENT" "WebSearch" "WebSearch mentioned" || true
assert_contains "$PROMPT_CONTENT" "WebFetch" "WebFetch mentioned" || true

# Test 3: Source provenance tags
echo ""
echo "Test 3: Source provenance..."
assert_contains "$PROMPT_CONTENT" "source: local" "source: local tag" || true
assert_contains "$PROMPT_CONTENT" "source: web" "source: web tag" || true
assert_contains "$PROMPT_CONTENT" "source: both" "source: both tag" || true

# Test 4: Cross-verification step
echo ""
echo "Test 4: Cross-verification..."
assert_contains "$PROMPT_CONTENT" "Cross-Verify" "Cross-verify step exists" || true
assert_contains "$PROMPT_CONTENT" "Compare local findings against web\|compare local findings against web" "Cross-verify comparison" || true

# Test 5: Conflict resolution
echo ""
echo "Test 5: Conflict resolution..."
assert_contains "$PROMPT_CONTENT" "Conflicts" "Conflicts section" || true
assert_contains "$PROMPT_CONTENT" "downgrade confidence\|Downgrade confidence\|downgrade.*confidence" "Confidence downgrade" || true

# Test 6: Cross-reference table
echo ""
echo "Test 6: Cross-reference table..."
assert_contains "$PROMPT_CONTENT" "Cross-Reference Table" "Cross-reference table" || true

# Test 7: Dual-source quality checklist
echo ""
echo "Test 7: Quality checklist..."
assert_contains "$PROMPT_CONTENT" "local sources" "Local sources in checklist" || true
assert_contains "$PROMPT_CONTENT" "web sources" "Web sources in checklist" || true

# Test 8: Dual-source rationalization entries
echo ""
echo "Test 8: Rationalization table..."
assert_contains "$PROMPT_CONTENT" "Local code is enough" "Local-only rationalization" || true
assert_contains "$PROMPT_CONTENT" "Web docs are enough" "Web-only rationalization" || true

# Test 9: Research method has 6 steps
echo ""
echo "Test 9: Research method steps..."
assert_contains "$PROMPT_CONTENT" "### 1. Clarify the Question" "Step 1" || true
assert_contains "$PROMPT_CONTENT" "### 2. Gather Local Evidence" "Step 2" || true
assert_contains "$PROMPT_CONTENT" "### 3. Gather Web Evidence" "Step 3" || true
assert_contains "$PROMPT_CONTENT" "### 4. Cross-Verify" "Step 4" || true
assert_contains "$PROMPT_CONTENT" "### 5. Analyze" "Step 5" || true
assert_contains "$PROMPT_CONTENT" "### 6. Write Research Report" "Step 6" || true

echo ""
report_failures
exit $?
