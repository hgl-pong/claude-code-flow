#!/usr/bin/env bash
# LONG_RUNNING: Behavioral e2e test for auto-mode research/planning path.
# Uses stream-json output to verify auto-mode skill invocation and research/planning guidance.
# Expect 5-10 minutes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "======================================"
echo " E2E Test: Auto-Mode Research Pipeline"
echo "======================================"
echo ""
echo "LONG_RUNNING: Expect 5-10 minutes."
echo ""

if [ "${RUN_LONG_TESTS:-}" != "true" ]; then
    echo "SKIP: Set RUN_LONG_TESTS=true to run long-running tests."
    exit 0
fi

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

cd "$TMPDIR"
git init >/dev/null 2>&1
cat > package.json <<'JSON'
{"scripts":{"test":"node test.js"}}
JSON
cat > test.js <<'JS'
console.log('ok')
JS

# Test 1: auto-mode skill triggers through namespaced slash command
echo "Test 1: auto-mode skill triggers..."
auto_log="$TMPDIR/auto-mode-output.jsonl"
claude -p "/claude-code-flow:auto-mode add a README with one sentence describing this research pipeline test project" \
    --plugin-dir "$REPO_ROOT" \
    --dangerously-skip-permissions \
    --max-turns 12 \
    --output-format stream-json \
    --verbose \
    > "$auto_log" 2>&1 || true

if grep -q '"name":"Skill"' "$auto_log" && grep -q '"skill":"claude-code-flow:auto-mode"' "$auto_log"; then
    pass "auto-mode skill triggered"
else
    fail "auto-mode skill NOT triggered"
    echo "  Skills found in output:"
    grep -o '"skill":"[^"]*"' "$auto_log" 2>/dev/null | sort -u || echo "    (none)"
fi

if grep -qE 'research|spec|plan|Decision trail|\.claude/auto' "$auto_log"; then
    pass "auto-mode output references research/planning/audit flow"
else
    fail "auto-mode output missing research/planning/audit references"
fi

echo ""

# Test 2: auto-mode audit/state output
echo "Test 2: auto-mode audit/state output..."
if [ -d ".claude/auto" ]; then
    pass ".claude/auto created"
else
    fail ".claude/auto not created"
fi

state_files=$(find .claude/auto -name state.json -type f 2>/dev/null || true)
if [ -n "$state_files" ]; then
    pass "state.json created"
else
    fail "state.json not created"
fi

if [ -f README.md ]; then
    pass "README.md created by auto-mode"
else
    fail "README.md not created"
fi

echo ""

# Test 3: verification command still works
echo "Test 3: project verification..."
if npm test >/tmp/auto-mode-research-npm.log 2>&1; then
    pass "npm test passed"
else
    fail "npm test failed"
    sed 's/^/    /' /tmp/auto-mode-research-npm.log
fi

echo ""

# Test 4: source/provenance/audit artifacts are inspectable
echo "Test 4: audit artifacts inspectable..."
if find .claude/auto -type f | grep -qE 'decisions\.md|spec\.md|plan\.md|runtime\.json'; then
    pass "audit artifacts created"
else
    fail "expected audit artifacts missing"
fi

if grep -R -qE 'Decision|Spec|Plan|Auto' .claude/auto 2>/dev/null; then
    pass "audit artifacts contain readable planning context"
else
    fail "audit artifacts missing readable planning context"
fi

echo ""
report_failures
exit $?
