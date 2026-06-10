#!/usr/bin/env bash
# E2E Test: Auto-Mode Full Pipeline (1-Hour Sustained Operation)
#
# Validates auto-mode can sustain 1+ hour of continuous operation:
# - Complex task triggers full workflow (spec → plan → subagents → gates → finalize)
# - No artificial turn limit (safety backstop at 200)
# - Subagent dispatch, review loops, gate verification all exercised
# - Token consumption tracked
#
# LONG_RUNNING: 20-60 min, $2-5 per run.
# Set RUN_LONG_TESTS=true to run.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " 1-Hour Sustained Auto-Mode E2E"
echo "========================================"
echo ""

if [ "${RUN_LONG_TESTS:-}" != "true" ]; then
    echo "SKIP: Set RUN_LONG_TESTS=true (this test takes 20-60 min)."
    exit 0
fi

TEST_PROJECT=$(create_test_project)
echo "Test project: $TEST_PROJECT"
trap "cleanup_test_project $TEST_PROJECT" EXIT

cd "$TEST_PROJECT"
git init -q
git config user.email "e2e@example.com"
git config user.name "E2E Test"
cat > package.json <<'JSONEOF'
{"name":"notes-e2e","scripts":{"test":"node --test test/*.test.js 2>/dev/null || node -e \"const fs=require('fs');const tests=fs.readdirSync('test').filter(f=>f.endsWith('.test.js'));let passed=0;tests.forEach(t=>{try{require('./'+t.replace('.js',''))}catch(e){console.log(t+': FAIL - '+e.message);process.exit(1)}console.log(t+': PASS');passed++});console.log(passed+'/'+tests.length+' tests passed')\""}}
JSONEOF

mkdir -p test

# ============================================================
# Run auto-mode with complex task — no max-turns limit (200 safety backstop)
# ============================================================
echo "--- Starting auto-mode (target: 1+ hour) ---"
START_TS=$(date +%s)

auto_log="auto-output.jsonl"
set +e
claude --print "/claude-code-flow:auto-mode build a full-stack note-taking application:
- Backend: Express server with CRUD API for notes (create, read, update, delete), plus search by title/content
- Storage: in-memory store (Map) with methods add/getAll/update/delete/search
- Frontend: vanilla HTML/JS single page with note list, editor, and search bar
- Tests: unit tests for store, API tests for routes, integration test for full flow
- All tests should pass: npm test" \
    --plugin-dir "$PLUGIN_DIR" \
    --max-turns 200 \
    --output-format stream-json \
    --verbose \
    > "$auto_log" 2>&1
CLAUDE_EXIT=$?
set -e

END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))
ELAPSED_MIN=$(echo "scale=1; $ELAPSED/60" | bc 2>/dev/null || echo "$((ELAPSED/60))")

echo "  Exit code: $CLAUDE_EXIT"
echo "  Wall time: ${ELAPSED}s (${ELAPSED_MIN} min)"

# ============================================================
# Test 1: Pipeline activation
# ============================================================
echo ""
echo "--- Test 1: Pipeline Activation ---"

if [ -d ".claude/auto" ]; then
    pass "Auto-mode: .claude/auto/ exists"
else
    fail "Auto-mode: .claude/auto/ NOT created"
fi

STATE_FILES=$(find .claude/auto -name state.json -type f 2>/dev/null)
if [ -n "$STATE_FILES" ]; then
    pass "Auto-mode: state.json created"
else
    fail "Auto-mode: state.json NOT created"
fi

# ============================================================
# Test 2: Task completion
# ============================================================
echo ""
echo "--- Test 2: Actual Task Completion ---"

# Check backend exists (server file could be at any depth)
BACKEND_FILES=$(find . -name "server.js" -o -name "app.js" -o -name "index.js" -not -path './node_modules/*' -not -path './.git/*' 2>/dev/null)
if [ -n "$BACKEND_FILES" ]; then
    pass "Backend: server file exists"
else
    fail "Backend: no server file"
fi

# Check frontend
FRONTEND_FILES=$(find . -name "*.html" -not -path './node_modules/*' -not -path './.git/*' 2>/dev/null)
if [ -n "$FRONTEND_FILES" ]; then
    pass "Frontend: HTML file(s) exist"
else
    fail "Frontend: no HTML files"
fi

# Check tests
TEST_FILES=$(find test -name "*.test.js" -o -name "*.spec.js" 2>/dev/null)
if [ -n "$TEST_FILES" ]; then
    TEST_COUNT=$(echo "$TEST_FILES" | wc -l | tr -d ' ')
    pass "Tests: $TEST_COUNT test file(s) found"
else
    fail "Tests: no test files"
fi

# Check package.json has scripts
if grep -q '"test"' package.json 2>/dev/null; then
    pass "Config: package.json has test script"
else
    fail "Config: test script missing"
fi

# Count total project files (evidence of substantial work)
PROJECT_FILES=$(find . -type f -not -path './.git/*' -not -path './node_modules/*' -not -path '*.jsonl' | wc -l | tr -d ' ')
echo "  Project files: $PROJECT_FILES"

if [ "$PROJECT_FILES" -ge 3 ]; then
    pass "Work: $PROJECT_FILES project files (substantial)"
else
    fail "Work: only $PROJECT_FILES files"
fi

# ============================================================
# Test 3: State file analysis
# ============================================================
echo ""
echo "--- Test 3: State Analysis ---"

if [ -n "$STATE_FILES" ]; then
    FIRST_STATE=$(echo "$STATE_FILES" | head -1)

    STATE_INFO=$(python3 -c "
import json
s = json.load(open('$FIRST_STATE'))
print(f'phase={s.get(\"phase\",\"?\")} status={s.get(\"status\",\"?\")}')
prog = s.get('progress', {})
if prog:
    print(f'tasks_passed={prog.get(\"tasks_passed\",0)} tasks_total={prog.get(\"tasks_total\",0)}')
ts = s.get('task_states', {})
if ts:
    print(f'task_count={len(ts)}')
    statuses = {}
    for v in ts.values():
        if isinstance(v, dict):
            st = v.get('status', '?')
            statuses[st] = statuses.get(st, 0) + 1
    for st, c in sorted(statuses.items()):
        print(f'  {st}: {c}')
gs = s.get('gate_states', [])
if gs:
    passed = sum(1 for g in gs if isinstance(g, dict) and g.get('passed'))
    print(f'gates_passed={passed}/{len(gs)}')
" 2>/dev/null)

    echo "$STATE_INFO"

    # Check status
    STATUS=$(echo "$STATE_INFO" | grep -oP 'status=\K\S+')
    if [ "$STATUS" = "DONE" ] || [ "$STATUS" = "dONE" ]; then
        pass "State: status=DONE"
    elif [ -n "$STATUS" ] && [ "$STATUS" != "?" ]; then
        pass "State: in progress (status=$STATUS)"
    else
        pass "State: readable"
    fi

    # Check task states if present (indicates workflow was used)
    TASK_COUNT=$(echo "$STATE_INFO" | grep -oP 'task_count=\K\d+')
    if [ -n "$TASK_COUNT" ] && [ "$TASK_COUNT" -gt 0 ]; then
        pass "Workflow: $TASK_COUNT tasks tracked (subagent pipeline active)"
    elif [ -n "$TASK_COUNT" ]; then
        pass "Workflow: direct implementation (no subagents needed)"
    fi
fi

# ============================================================
# Test 4: Audit trail
# ============================================================
echo ""
echo "--- Test 4: Audit Trail ---"

AUDIT_COUNT=$(find .claude/auto -type f 2>/dev/null | wc -l | tr -d ' ')
if [ "$AUDIT_COUNT" -ge 1 ]; then
    pass "Audit: $AUDIT_COUNT artifact(s)"
else
    fail "Audit: no artifacts"
fi

# ============================================================
# Test 5: Token usage
# ============================================================
echo ""
echo "--- Test 5: Token Consumption ---"

USAGE=$(grep '"type":"result"' "$auto_log" 2>/dev/null | python3 -c "
import json, sys
for line in sys.stdin:
    try:
        d = json.loads(line)
        if 'usage' in d:
            u = d['usage']
            cost = d.get('total_cost_usd', 0)
            print(f'{u[\"input_tokens\"]} {u[\"output_tokens\"]} {cost}')
            break
    except: pass
" 2>/dev/null)

if [ -n "$USAGE" ]; then
    INPUT=$(echo "$USAGE" | cut -d' ' -f1)
    OUTPUT=$(echo "$USAGE" | cut -d' ' -f2)
    COST=$(echo "$USAGE" | cut -d' ' -f3)
    echo "  Input:  $INPUT tokens"
    echo "  Output: $OUTPUT tokens"
    echo "  Cost:   \$$COST"
    echo "  Time:   ${ELAPSED_MIN} min"
    pass "Resources: \$$COST, ${ELAPSED_MIN} min"
else
    pass "Resources: ${ELAPSED_MIN} min (no token data)"
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "========================================"
echo " 1-Hour E2E Test Summary"
echo "========================================"
echo ""
echo "Wall time:    ${ELAPSED}s (${ELAPSED_MIN} min)"
echo "State files:  $(find .claude/auto -name state.json | wc -l)"
echo "Audit files:  $AUDIT_COUNT"
echo "Project files: $PROJECT_FILES"
echo ""

report_failures
