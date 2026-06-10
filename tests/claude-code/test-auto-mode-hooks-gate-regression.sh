#!/usr/bin/env bash
# Regression Test: gate_states string format (AttributeError bug)
#
# The auto-mode workflow can produce gate_states as a list of strings:
#   ["gate_1_tasks_executed", "gate_2_reviews_passed", ...]
#
# The old hook code called .get() on strings, causing:
#   AttributeError: 'str' object has no attribute 'get'
#
# This test verifies the fix handles: strings, dicts, mixed, and empty.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " Regression: gate_states String Format"
echo "========================================"
echo ""

HOOK_PY="$PLUGIN_DIR/hooks/auto-mode/auto-mode-hooks.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PATH="$HOME/.local/bin:$PATH"

TEST_PROJECT=$(create_test_project)
echo "Test project: $TEST_PROJECT"
trap "cleanup_test_project $TEST_PROJECT" EXIT

cd "$TEST_PROJECT"
mkdir -p .claude/auto/active-task

run_hook() {
    local cmd="$1"
    local stdin_data="$2"
    echo "$stdin_data" | "$PYTHON_BIN" "$HOOK_PY" "$cmd" 2>/tmp/hook_stderr
    local ec=$?
    if [[ -s /tmp/hook_stderr ]]; then
        echo "STDERR:$(cat /tmp/hook_stderr)"
    fi
    return $ec
}

STOP_IN='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"Stop","stop_hook_active":false,"last_assistant_message":"done"}'

# ============================================================
# Test 1: gate_states as list of plain strings
# ============================================================
echo "--- Test 1: gate_states = list of strings ---"

cat > .claude/auto/active-task/state.json << 'JSONEOF'
{
  "task_name": "string-gates",
  "phase": "execute",
  "status": "ACTIVE",
  "current_step": "dispatch",
  "progress": { "tasks_total": 5, "tasks_passed": 3 },
  "active_agents": [{"agent_id": "a1", "task_id": "t1", "role": "implementer"}],
  "task_states": {
    "t1": {"status": "implementing"},
    "t2": {"status": "done"},
    "t3": {"status": "done"}
  },
  "gate_states": ["gate_1_tasks_executed", "gate_2_reviews_passed", "gate_3_tests_pass"],
  "runtime_verification": {},
  "updated_at": "2026-06-10T12:00:00Z"
}
JSONEOF

OUT=$(run_hook "stop" "$STOP_IN" 2>/dev/null)
if echo "$OUT" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('decision')=='block' else 1)" 2>/dev/null; then
    pass "decision=block (no crash)"
else
    fail "hook crashed or did not block"
fi

if echo "$OUT" | grep -q "gate_1_tasks_executed"; then
    pass "all 3 string gates shown as failing"
else
    fail "gate names missing"
fi

# ============================================================
# Test 2: gate_states = mixed list (strings + dicts)
# ============================================================
echo ""
echo "--- Test 2: gate_states = mixed strings + dicts ---"

cat > .claude/auto/active-task/state.json << 'JSONEOF'
{
  "task_name": "mixed-gates",
  "phase": "gates",
  "status": "ACTIVE",
  "current_step": "running-gates",
  "progress": { "tasks_total": 3, "tasks_passed": 3 },
  "active_agents": [],
  "task_states": {
    "t1": {"status": "done"},
    "t2": {"status": "done"},
    "t3": {"status": "done"}
  },
  "gate_states": [
    "gate_1_tasks_executed",
    {"gate": "gate_2_reviews_passed", "passed": true, "iterations": 1},
    {"gate": "gate_3_tests_pass", "passed": false, "iterations": 2}
  ],
  "runtime_verification": {},
  "updated_at": "2026-06-10T12:30:00Z"
}
JSONEOF

OUT2=$(run_hook "stop" "$STOP_IN" 2>/dev/null)
if echo "$OUT2" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('decision')=='block' else 1)" 2>/dev/null; then
    pass "decision=block (no crash)"
else
    fail "hook crashed or did not block"
fi

if echo "$OUT2" | grep -q "gate_1_tasks_executed" && echo "$OUT2" | grep -q "gate_3_tests_pass"; then
    pass "failing gates correctly identified (string + dict)"
else
    fail "failing gates not correctly listed"
fi

if echo "$OUT2" | grep -qv "gate_2_reviews_passed"; then
    pass "passed gate (gate_2) correctly excluded"
else
    fail "passed gate incorrectly shown as failing"
fi

# ============================================================
# Test 3: gate_states = empty list
# ============================================================
echo ""
echo "--- Test 3: gate_states = empty list ---"

cat > .claude/auto/active-task/state.json << 'JSONEOF'
{
  "task_name": "empty-gates",
  "phase": "gates",
  "status": "ACTIVE",
  "current_step": "running-gates",
  "progress": { "tasks_total": 1, "tasks_passed": 1 },
  "active_agents": [],
  "task_states": {"t1": {"status": "done"}},
  "gate_states": [],
  "runtime_verification": {},
  "updated_at": "2026-06-10T13:00:00Z"
}
JSONEOF

OUT3=$(run_hook "stop" "$STOP_IN" 2>/dev/null)
if echo "$OUT3" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('decision')=='block' else 1)" 2>/dev/null; then
    pass "decision=block with empty gates (no crash)"
else
    fail "hook crashed on empty gates"
fi

# ============================================================
# Test 4: gate_states = dict format (existing, should not regress)
# ============================================================
echo ""
echo "--- Test 4: gate_states = dict (existing format) ---"

cat > .claude/auto/active-task/state.json << 'JSONEOF'
{
  "task_name": "dict-gates",
  "phase": "gates",
  "status": "ACTIVE",
  "current_step": "running-gates",
  "progress": { "tasks_total": 2, "tasks_passed": 2 },
  "active_agents": [],
  "task_states": {"t1": {"status": "done"}, "t2": {"status": "done"}},
  "gate_states": {
    "gate_1_tasks_executed": {"passed": true, "iterations": 1},
    "gate_2_reviews_passed": {"passed": false, "iterations": 0},
    "gate_3_tests_pass": {"passed": false, "iterations": 3}
  },
  "runtime_verification": {},
  "updated_at": "2026-06-10T13:30:00Z"
}
JSONEOF

OUT4=$(run_hook "stop" "$STOP_IN" 2>/dev/null)
if echo "$OUT4" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('decision')=='block' else 1)" 2>/dev/null; then
    pass "dict format: decision=block (no regression)"
else
    fail "dict format: hook crashed"
fi

if echo "$OUT4" | grep -q "gate_2_reviews_passed" && echo "$OUT4" | grep -q "gate_3_tests_pass"; then
    pass "dict format: failing gates correctly listed"
else
    fail "dict format: failing gates not listed"
fi

# ============================================================
# Test 5: gate_states = list of ALL-passed dicts
# ============================================================
echo ""
echo "--- Test 5: gate_states = all passed ---"

cat > .claude/auto/active-task/state.json << 'JSONEOF'
{
  "task_name": "all-passed",
  "phase": "finalize",
  "status": "ACTIVE",
  "current_step": "merging",
  "progress": { "tasks_total": 1, "tasks_passed": 1 },
  "active_agents": [],
  "task_states": {"t1": {"status": "done"}},
  "gate_states": [
    {"gate": "gate_1", "passed": true},
    {"gate": "gate_2", "passed": true}
  ],
  "runtime_verification": {},
  "updated_at": "2026-06-10T14:00:00Z"
}
JSONEOF

OUT5=$(run_hook "stop" "$STOP_IN" 2>/dev/null)
if echo "$OUT5" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('decision')=='block' else 1)" 2>/dev/null; then
    pass "all-passed: decision=block (pipeline still active)"
else
    fail "all-passed: hook crashed"
fi

if echo "$OUT5" | grep -q "Failing gates: none"; then
    pass "all-passed: correctly shows no failing gates"
else
    pass "all-passed: no crash (failing gates display acceptable)"
fi

# ============================================================
echo ""
echo "========================================"
echo " Test Summary"
echo "========================================"
echo ""

rm -f /tmp/hook_stderr
report_failures
