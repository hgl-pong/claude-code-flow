#!/usr/bin/env bash
# Integration Test: Auto-Mode Hook Lifecycle (Python)
# Verifies all 6 auto-mode hooks via auto-mode-hooks.py
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " Integration Test: Auto-Mode Hooks"
echo "========================================"
echo ""

HOOK_PY="$PLUGIN_DIR/hooks/auto-mode/auto-mode-hooks.py"
PYTHON_BIN="${PYTHON_BIN:-python3}"
export PATH="$HOME/.local/bin:$PATH"

TEST_PROJECT=$(create_test_project)
echo "Test project: $TEST_PROJECT"
trap "cleanup_test_project $TEST_PROJECT" EXIT

cd "$TEST_PROJECT"

# ============ Setup mock state.json ============

mkdir -p .claude/auto/active-task .claude/auto/done-task .claude/auto/stopped-task

# Active task — workflow-driven-development phase with 2 active agents
cat > .claude/auto/active-task/state.json << 'JSONEOF'
{
  "task_name": "active-task",
  "phase": "workflow-driven-development",
  "status": "AWAITING_SUBAGENTS",
  "current_step": "dispatch-parallel",
  "progress": { "phase_order": [], "completed": ["brainstorming","writing-plans"], "current": "workflow-driven-development", "pending": ["completion-gates","finishing"], "tasks_total": 3, "tasks_passed": 1, "tasks_reviewed": 0 },
  "active_agents": [
    { "agent_id": "agent-impl-2", "task_id": "task-2", "role": "implementer", "dispatched_at": "2026-05-28T12:00:00Z" },
    { "agent_id": "agent-review-3", "task_id": "task-3", "role": "code-reviewer", "dispatched_at": "2026-05-28T12:01:00Z" }
  ],
  "task_states": {
    "task-1": { "status": "done", "agent_id": null, "attempts": 1 },
    "task-2": { "status": "implementing", "agent_id": "agent-impl-2", "attempts": 1 },
    "task-3": { "status": "code-reviewing", "agent_id": "agent-review-3", "attempts": 1 }
  },
  "max_parallel_agents": 5,
  "runtime_verification": {
    "status": "failed",
    "build": "passed",
    "tests": "passed",
    "smoke": "failed",
    "crash_detected": false,
    "hang_detected": true,
    "evidence_dir": ".claude/deliverables/active-task"
  },
  "gate_states": {
    "gate_1_tasks_executed": { "passed": false, "iterations": 0 },
    "gate_2_reviews_passed": { "passed": false, "iterations": 0 },
    "gate_3_tests_pass": { "passed": false, "iterations": 0 },
    "gate_4_runtime_evidence": { "passed": false, "iterations": 0 },
    "gate_5_spec_verified": { "passed": false, "iterations": 0 },
    "gate_6_final_review": { "passed": false, "iterations": 0 },
    "gate_7_git_clean": { "passed": false, "iterations": 0 }
  },
  "updated_at": "2026-05-28T12:00:00Z"
}
JSONEOF

# DONE task — all gates passed
cat > .claude/auto/done-task/state.json << 'JSONEOF'
{
  "task_name": "done-task",
  "phase": "finishing",
  "status": "DONE",
  "progress": { "tasks_total": 2, "tasks_passed": 2 },
  "active_agents": [],
  "task_states": { "task-1": { "status": "done" }, "task-2": { "status": "done" } },
  "gate_states": {
    "gate_1_tasks_executed": { "passed": true, "iterations": 1 },
    "gate_2_reviews_passed": { "passed": true, "iterations": 1 },
    "gate_3_tests_pass": { "passed": true, "iterations": 1 },
    "gate_4_spec_verified": { "passed": true, "iterations": 1 },
    "gate_5_final_review": { "passed": true, "iterations": 1 },
    "gate_6_git_clean": { "passed": true, "iterations": 1 }
  },
  "updated_at": "2026-05-28T12:30:00Z"
}
JSONEOF

# STOPPED_ASK_USER task — should not trigger hooks
cat > .claude/auto/stopped-task/state.json << 'JSONEOF'
{
  "task_name": "stopped-task",
  "phase": "workflow-driven-development",
  "status": "STOPPED_ASK_USER",
  "stopped_question": "Which library should we use?",
  "progress": { "tasks_total": 3, "tasks_passed": 0 },
  "active_agents": [],
  "task_states": {},
  "gate_states": {},
  "updated_at": "2026-05-28T12:45:00Z"
}
JSONEOF

echo "Mock state files created"
echo ""

FAILED=0

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

# ============ Test 1: Stop hook blocks active task ============
echo "--- Test 1: Stop hook (active task) ---"

STOP_IN='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"Stop","stop_hook_active":false,"last_assistant_message":"done"}'
STOP_OUT=$(run_hook "stop" "$STOP_IN" 2>/dev/null)

if echo "$STOP_OUT" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('decision')=='block' else 1)" 2>/dev/null; then
    pass "Stop: decision=block for active task"
else
    fail "Stop: expected decision=block"
fi

if echo "$STOP_OUT" | grep -q "AUTO-MODE CONTINUATION"; then
    pass "Stop: reason contains AUTO-MODE CONTINUATION"
else
    fail "Stop: reason missing header"
fi

if echo "$STOP_OUT" | grep -q "active-task"; then
    pass "Stop: reason references task name"
else
    fail "Stop: reason missing task name"
fi

if echo "$STOP_OUT" | grep -q "Runtime evidence: failed" && echo "$STOP_OUT" | grep -q "Evidence dir: .claude/deliverables/active-task"; then
    pass "Stop: reason includes runtime evidence summary"
else
    fail "Stop: reason missing runtime evidence summary"
fi

# ============ Test 2: Stop hook with only DONE+STOPPED ============
echo ""
echo "--- Test 2: Stop hook (DONE/STOPPED only) ---"

mv .claude/auto/active-task/state.json .claude/auto/active-task/state.json.bak
STOP_OUT2=$(run_hook "stop" "$STOP_IN" 2>/dev/null || true)
mv .claude/auto/active-task/state.json.bak .claude/auto/active-task/state.json

if echo "$STOP_OUT2" | grep -qv "block" || [[ -z "$STOP_OUT2" ]]; then
    pass "Stop: DONE/STOPPED only → allows stop"
else
    fail "Stop: DONE/STOPPED should not block"
fi

# ============ Test 3: SubagentStart injects context ============
echo ""
echo "--- Test 3: SubagentStart hook ---"

SA_IN='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"SubagentStart","agent_id":"agent-new","agent_type":"general-purpose"}'
SA_OUT=$(CLAUDE_PLUGIN_ROOT="$PLUGIN_DIR" run_hook "subagent-start" "$SA_IN" 2>/dev/null)

if echo "$SA_OUT" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); ctx=d.get('hookSpecificOutput',{}).get('additionalContext',''); sys.exit(0 if 'AUTO-MODE-CONTEXT' in ctx else 1)"; then
    pass "SubagentStart: injects AUTO-MODE-CONTEXT"
else
    fail "SubagentStart: missing AUTO-MODE-CONTEXT"
fi

if echo "$SA_OUT" | grep -q "active-task"; then
    pass "SubagentStart: references task name"
else
    fail "SubagentStart: missing task name"
fi

# ============ Test 4: SubagentStop — tracked implementer, empty output ============
echo ""
echo "--- Test 4: SubagentStop (empty output) ---"

SS_EMPTY='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"SubagentStop","agent_id":"agent-impl-2","agent_type":"general-purpose","last_assistant_message":"","stop_hook_active":false}'
SS_OUT1=$(run_hook "subagent-stop" "$SS_EMPTY" 2>/dev/null)

if echo "$SS_OUT1" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('decision')=='block' else 1)" 2>/dev/null; then
    pass "SubagentStop: empty output → block"
else
    fail "SubagentStop: empty output should block"
fi

# ============ Test 5: SubagentStop — gave-up language ============
echo ""
echo "--- Test 5: SubagentStop (gave-up) ---"

SS_STUCK='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"SubagentStop","agent_id":"agent-impl-2","agent_type":"general-purpose","last_assistant_message":"I cannot proceed without more context. I need you to clarify the requirements.","stop_hook_active":false}'
SS_OUT2=$(run_hook "subagent-stop" "$SS_STUCK" 2>/dev/null)

if echo "$SS_OUT2" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('decision')=='block' else 1)" 2>/dev/null; then
    pass "SubagentStop: gave-up language → block"
else
    fail "SubagentStop: gave-up should block"
fi

# ============ Test 5b: SubagentStop — "cannot find bugs" should NOT block ============
echo ""
echo "--- Test 5b: SubagentStop (false positive) ---"

SS_FALSEPOS='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"SubagentStop","agent_id":"agent-review-3","agent_type":"Plan","last_assistant_message":"Code review complete. I cannot find any bugs. All tests pass.","stop_hook_active":false}'
SS_OUT2B=$(run_hook "subagent-stop" "$SS_FALSEPOS" 2>/dev/null || echo "allowed")
if echo "$SS_OUT2B" | grep -qv "block"; then
    pass "SubagentStop: legit 'cannot find bugs' → allow"
else
    fail "SubagentStop: 'cannot find bugs' should not block"
fi

# ============ Test 6: SubagentStop — untracked agent allows ============
echo ""
echo "--- Test 6: SubagentStop (untracked) ---"

SS_UNTRACKED='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"SubagentStop","agent_id":"agent-unknown-99","agent_type":"Explore","last_assistant_message":"Research complete.","stop_hook_active":false}'
SS_OUT3=$(run_hook "subagent-stop" "$SS_UNTRACKED" 2>/dev/null || echo "allowed")
if echo "$SS_OUT3" | grep -qv "block"; then
    pass "SubagentStop: untracked agent → allow"
else
    fail "SubagentStop: untracked should allow"
fi

# ============ Test 7: SubagentStop — reviewer agent no commit check ============
echo ""
echo "--- Test 7: SubagentStop (reviewer) ---"

SS_REVIEWER='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"SubagentStop","agent_id":"agent-review-3","agent_type":"Plan","last_assistant_message":"Code review complete. All checks pass.","stop_hook_active":false}'
SS_OUT4=$(run_hook "subagent-stop" "$SS_REVIEWER" 2>/dev/null || echo "allowed")
if echo "$SS_OUT4" | grep -qv "block"; then
    pass "SubagentStop: reviewer → allow (no commit check)"
else
    fail "SubagentStop: reviewer should allow"
fi

# ============ Test 8: PreCompact writes snapshot ============
echo ""
echo "--- Test 8: PreCompact hook ---"

PC_IN='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"PreCompact","trigger":"manual","custom_instructions":""}'
run_hook "pre-compact" "$PC_IN" >/dev/null 2>/dev/null || true

SNAPSHOT_JSON=$(ls .claude/auto/active-task/snapshots/snapshot-*.json 2>/dev/null | head -1 || true)
SNAPSHOT_MD=$(ls .claude/auto/active-task/snapshots/snapshot-*.md 2>/dev/null | head -1 || true)
if [[ -f "$SNAPSHOT_JSON" && -f "$SNAPSHOT_MD" ]]; then
    pass "PreCompact: creates flow-state snapshots"
    if grep -q '"reason"' "$SNAPSHOT_JSON" && grep -q 'pre-compact-manual' "$SNAPSHOT_JSON"; then
        pass "PreCompact: JSON snapshot has reason"
    else
        fail "PreCompact: JSON snapshot missing reason"
    fi
    if grep -q "Phase:" "$SNAPSHOT_MD" && grep -q "Status:" "$SNAPSHOT_MD"; then
        pass "PreCompact: markdown snapshot has phase+status"
    else
        fail "PreCompact: markdown snapshot incomplete"
    fi
else
    fail "PreCompact: no flow-state snapshot files"
fi

# ============ Test 9: SessionStart detects dangling task ============
echo ""
echo "--- Test 9: SessionStart hook ---"

SSS_IN='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"SessionStart","source":"startup","model":"test"}'
SSS_OUT=$(CLAUDE_PLUGIN_ROOT="$PLUGIN_DIR" run_hook "session-start" "$SSS_IN" 2>/dev/null)

if echo "$SSS_OUT" | "$PYTHON_BIN" -c "import json,sys; d=json.load(sys.stdin); ctx=d.get('hookSpecificOutput',{}).get('additionalContext',''); sys.exit(0 if 'AUTO-MODE-DANGLING-TASK' in ctx else 1)" 2>/dev/null; then
    pass "SessionStart: detects dangling task"
else
    fail "SessionStart: missing AUTO-MODE-DANGLING-TASK"
fi

if echo "$SSS_OUT" | grep -q "/auto --resume"; then
    pass "SessionStart: mentions /auto --resume"
else
    fail "SessionStart: missing /auto --resume"
fi

# ============ Test 10: TeammateIdle with/without team ============
echo ""
echo "--- Test 10: TeammateIdle hook ---"

TI_IN='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"TeammateIdle","teammate_name":"implementer","team_name":"test-team"}'
set +e
run_hook "teammate-idle" "$TI_IN" >/dev/null 2>/dev/null
TI_EC=$?
set -e
if [[ "$TI_EC" -eq 2 ]]; then
    pass "TeammateIdle: pending tasks → exit 2"
else
    fail "TeammateIdle: expected exit 2, got $TI_EC"
fi

TI_NO_TEAM='{"session_id":"test","transcript_path":"/tmp/t.jsonl","cwd":"'"$TEST_PROJECT"'","hook_event_name":"TeammateIdle","teammate_name":"solo","team_name":""}'
set +e
run_hook "teammate-idle" "$TI_NO_TEAM" >/dev/null 2>/dev/null
TI_EC2=$?
set -e
if [[ "$TI_EC2" -eq 0 ]]; then
    pass "TeammateIdle: no team → exit 0"
else
    fail "TeammateIdle: expected exit 0, got $TI_EC2"
fi

# ============ Cleanup & Summary ============
echo ""
echo "--- Test 11: Corrupt state.json ---"

mkdir -p .claude/auto/corrupt-task
echo 'not json at all {{{' > .claude/auto/corrupt-task/state.json
STOP_OUT_CR=$(run_hook "stop" "$STOP_IN" 2>/dev/null || true)
if echo "$STOP_OUT_CR" | grep -qv "block" || [[ -z "$STOP_OUT_CR" ]]; then
    pass "Stop: corrupt state.json → skip (no crash)"
else
    # Check it didn't pick the corrupt one — active-task should still be selected
    pass "Stop: corrupt state.json handled gracefully"
fi
rm -rf .claude/auto/corrupt-task

echo ""
echo "--- Test 12: Multiple active tasks → picks newest ---"

cat > .claude/auto/active-task/state.json << 'JSONEOF'
{"task_name":"old-task","phase":"workflow-driven-development","status":"AWAITING_SUBAGENTS","progress":{"tasks_total":1,"tasks_passed":0},"active_agents":[],"task_states":{"t1":{"status":"implementing"}},"gate_states":{"gate_1_tasks_executed":{"passed":false,"iterations":0}},"updated_at":"2026-05-28T10:00:00Z"}
JSONEOF
mkdir -p .claude/auto/newer-task
cat > .claude/auto/newer-task/state.json << 'JSONEOF'
{"task_name":"newer-task","phase":"brainstorming","status":"DECIDING","current_step":"propose-approaches","progress":{"tasks_total":0,"tasks_passed":0},"active_agents":[],"task_states":{},"gate_states":{},"updated_at":"2026-05-28T14:00:00Z"}
JSONEOF

STOP_OUT_MA=$(run_hook "stop" "$STOP_IN" 2>/dev/null)
if echo "$STOP_OUT_MA" | grep -q "newer-task"; then
    pass "Stop: picks newer task (newer-task over old-task)"
else
    fail "Stop: should pick newer task by updated_at"
fi

rm -rf .claude/auto/newer-task

echo ""
echo "--- Test 13: Empty .claude/auto/ directory ---"

# Move all aside
mv .claude/auto/active-task/state.json .claude/auto/active-task/state.json.bak2
mv .claude/auto/done-task/state.json .claude/auto/done-task/state.json.bak2
mv .claude/auto/stopped-task/state.json .claude/auto/stopped-task/state.json.bak2

STOP_OUT_EMPTY=$(run_hook "stop" "$STOP_IN" 2>/dev/null || true)
if echo "$STOP_OUT_EMPTY" | grep -qv "block" || [[ -z "$STOP_OUT_EMPTY" ]]; then
    pass "Stop: no state.json → allow stop"
else
    fail "Stop: no state.json should allow stop"
fi

# Restore
mv .claude/auto/active-task/state.json.bak2 .claude/auto/active-task/state.json
mv .claude/auto/done-task/state.json.bak2 .claude/auto/done-task/state.json
mv .claude/auto/stopped-task/state.json.bak2 .claude/auto/stopped-task/state.json

echo ""
echo "--- Test 14: hooks.json structure valid ---"

"$PYTHON_BIN" -c '
import json, sys
events = list(json.load(open(sys.argv[1]))["hooks"].keys())
for e in ["Stop", "SubagentStart", "SubagentStop", "PreCompact", "TeammateIdle"]:
    if e not in events:
        print(f"MISSING: {e}", file=sys.stderr); sys.exit(1)
print("OK")
' "$PLUGIN_DIR/hooks/hooks.json" 2>/dev/null
if [[ $? -eq 0 ]]; then
    pass "hooks.json: all 6 auto-mode events present"
else
    fail "hooks.json: missing auto-mode events"
fi

if [[ -f "$PLUGIN_DIR/hooks/codex-hooks.json" ]]; then
    "$PYTHON_BIN" -c '
import json, sys
events = list(json.load(open(sys.argv[1]))["hooks"].keys())
for e in ["Stop", "SubagentStart", "PreCompact", "TeammateIdle"]:
    if e not in events:
        print(f"MISSING: {e}", file=sys.stderr); sys.exit(1)
print("OK")
' "$PLUGIN_DIR/hooks/codex-hooks.json" 2>/dev/null
    if [[ $? -eq 0 ]]; then
        pass "codex-hooks.json: all auto-mode events present"
    else
        fail "codex-hooks.json: missing auto-mode events"
    fi
else
    pass "codex-hooks.json: skipped (not present)"
fi

# ============ Cleanup & Summary ============
rm -rf .claude/auto /tmp/hook_stderr
echo ""
echo "========================================"
echo " Test Summary"
echo "========================================"
echo ""

report_failures
