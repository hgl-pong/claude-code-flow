#!/usr/bin/env bash
# Test: Plugin Loading
# Verifies that the claude-code-flow plugin loads correctly in OpenCode
set -euo pipefail

FAILURES=0

pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; FAILURES=$((FAILURES + 1)); }

report_failures() {
    if [ "$FAILURES" -eq 0 ]; then
        echo ""
        echo "=== All plugin loading tests passed ==="
        return 0
    else
        echo ""
        echo "=== $FAILURES plugin loading test(s) FAILED ==="
        return 1
    fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Test: Plugin Loading ==="

# Source setup to create isolated environment
source "$SCRIPT_DIR/setup.sh"

# Trap to cleanup on exit
trap cleanup_test_env EXIT

plugin_link="$OPENCODE_CONFIG_DIR/plugins/claude-code-flow.js"

# Test 1: Verify plugin file exists and is registered
echo "Test 1: Checking plugin registration..."
if [ -L "$plugin_link" ]; then
    pass "Plugin symlink exists"
else
    fail "Plugin symlink not found at $plugin_link"
fi

# Verify symlink target exists
if [ -f "$(readlink -f "$plugin_link")" ]; then
    pass "Plugin symlink target exists"
else
    fail "Plugin symlink target does not exist"
fi

# Test 2: Verify skills directory is populated
echo "Test 2: Checking skills directory..."
skill_count=$(find "$CCFLOW_SKILLS_DIR" -name "SKILL.md" | wc -l)
if [ "$skill_count" -gt 0 ]; then
    pass "Found $skill_count skills"
else
    fail "No skills found in $CCFLOW_SKILLS_DIR"
fi

# Test 3: Check using-claude-code-flow skill exists (critical for bootstrap)
echo "Test 3: Checking using-claude-code-flow skill (required for bootstrap)..."
if [ -f "$CCFLOW_SKILLS_DIR/using-claude-code-flow/SKILL.md" ]; then
    pass "using-claude-code-flow skill exists"
else
    fail "using-claude-code-flow skill not found (required for bootstrap)"
fi

# Test 4: Verify plugin JavaScript syntax (basic check)
echo "Test 4: Checking plugin JavaScript syntax..."
if node --check "$CCFLOW_PLUGIN_FILE" 2>/dev/null; then
    pass "Plugin JavaScript syntax is valid"
else
    fail "Plugin has JavaScript syntax errors"
fi

# Test 5: Verify bootstrap text does not reference a hardcoded skills path
echo "Test 5: Checking bootstrap does not advertise a wrong skills path..."
if grep -q 'configDir}/skills/claude-code-flow/' "$CCFLOW_PLUGIN_FILE"; then
    fail "Plugin still references old configDir skills path"
else
    pass "Plugin does not advertise a misleading skills path"
fi

# Test 6: Verify personal test skill was created
echo "Test 6: Checking test fixtures..."
if [ -f "$OPENCODE_CONFIG_DIR/skills/personal-test/SKILL.md" ]; then
    pass "Personal test skill fixture created"
else
    fail "Personal test skill fixture not found"
fi

echo ""

report_failures
exit $?
