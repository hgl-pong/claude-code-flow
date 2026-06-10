#!/usr/bin/env bash
# E2E Test: Auto-Mode Long Task — CLI Tool Demo
#
# Uses a test-driven CLI tool as the demo task. Forces iteration via:
# - 40+ test cases across 8 test files
# - Tests MUST pass before DONE
# - Each test-file cycle = implement + test + fix + retest
# - npm install time
# - Subagent dispatch for parallel test implementation
#
# The prompt is designed to produce 30-90 minutes of sustained work.
# The "secret" is test-driven requirements that force fix cycles.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " Long-Task E2E: CLI Tool Demo"
echo "========================================"
echo ""

if [ "${RUN_LONG_TESTS:-}" != "true" ]; then
    echo "SKIP: Set RUN_LONG_TESTS=true"
    exit 0
fi

TEST_PROJECT=$(create_test_project)
cd "$TEST_PROJECT"
git init -q && git config user.email "test@test.com" && git config user.name "Test"

cat > package.json <<'JSON'
{"name":"taskman","scripts":{"test":"node run-tests.js"}}
JSON

cat > run-tests.js <<'JS'
const fs=require('fs'),path=require('path');
function find(dir){let r=[];fs.readdirSync(dir).forEach(f=>{const p=path.join(dir,f);
if(fs.statSync(p).isDirectory())r=r.concat(find(p));else if(f.endsWith('.test.js'))r.push(p)});return r}
let passed=0,failed=0;const tests=find('test');
console.log(`Running ${tests.length} test files...\n`);
tests.forEach(t=>{try{process.stdout.write(path.basename(t)+': ');require(path.resolve(t));
console.log('PASS');passed++}catch(e){console.log('FAIL -',e.message.split('\n')[0]);failed++}});
console.log(`\n${passed}/${passed+failed} test files passed`);
if(failed)process.exit(1);
JS

mkdir -p test/unit test/integration
echo "// tests go here" > test/.gitkeep

START_TS=$(date +%s)
echo "Start: $(date +%H:%M:%S)"
echo ""

# =============================================================
# THE PROMPT — designed to produce 1+ hour of sustained work
# =============================================================
claude --print "/claude-code-flow:auto-mode build a Task Manager CLI tool called 'taskman'. This is a test-driven task — ALL tests must pass before DONE. Use subagents for parallel implementation.

## What to Build

**CLI tool (cli.js)** with these subcommands:
  taskman add <title> [--priority=low|medium|high] [--due=<date>] — creates a task, prints ID
  taskman list [--status=pending|done|all] [--priority=low|medium|high] — lists tasks in table format
  taskman done <id> — marks task as done
  taskman update <id> [--title=<new>] [--priority=<new>] [--due=<new>] — updates fields
  taskman delete <id> — deletes task, prints confirmation
  taskman search <query> — searches title/description, prints matches
  taskman stats — prints counts: total, done, pending, by priority
  taskman export [--format=json|csv] — exports all tasks to stdout

**Data store (src/store.js):**
  Store class with methods: add(task), get(id), list(filter), update(id, patch), delete(id), search(query), stats()
  Persists to .taskman-data/tasks.json, loads on startup
  Auto-increment IDs starting from 1

**Task model (src/task.js):**
  Properties: id, title, description, priority, status, dueDate, createdAt, completedAt
  Validation: title required (non-empty), priority in [low,medium,high], dueDate ISO8601 or null
  Factory: createTask(raw) returns validated task or throws ValidationError

**Error handling (src/errors.js):**
  ValidationError, NotFoundError, DuplicateError classes

## Test Requirements (MUST ALL PASS)

**8 test files, 50+ test cases total:**

test/unit/task.test.js — 8+ tests:
  - createTask with valid data
  - createTask throws on missing title
  - createTask throws on invalid priority
  - createTask sets defaults (status:pending, priority:medium)
  - createTask generates createdAt
  - createTask accepts optional description
  - createTask with dueDate
  - createTask with ISO8601 date format

test/unit/store.test.js — 8+ tests:
  - add returns task with id
  - add increments IDs
  - get returns task by id
  - get throws NotFoundError for missing id
  - list returns all tasks
  - list filters by status
  - list filters by priority
  - update modifies fields
  - update throws NotFoundError
  - delete removes task
  - delete throws NotFoundError
  - search finds by title
  - stats returns correct counts

test/unit/cli-parser.test.js — 6+ tests:
  - parses 'add Task title' correctly
  - parses 'add Title --priority=high'
  - parses 'add Title --due=2026-12-31'
  - parses 'list --status=done'
  - parses 'done 42'
  - rejects unknown subcommand

test/integration/add-list.test.js — 6+ tests:
  - add task and list shows it
  - add 3 tasks and list shows all with correct order
  - add with different priorities, list --priority=high
  - add with due date, verify in list output
  - add with empty title (should error gracefully)
  - add duplicate (same title, different IDs)

test/integration/done-update-delete.test.js — 6+ tests:
  - add then done, verify status changed
  - done non-existent task (error handling)
  - update title of existing task
  - update priority and due date
  - delete task, verify removed
  - delete non-existent task (error handling)

test/integration/search-stats.test.js — 6+ tests:
  - search by title finds matches
  - search by partial title
  - search returns empty for no matches
  - stats shows correct total/done/pending
  - stats shows by-priority breakdown
  - stats after adding then completing tasks

test/integration/export.test.js — 5+ tests:
  - export JSON format produces valid JSON array
  - export CSV format has headers
  - export CSV format has correct row count
  - export after delete excludes deleted task
  - export empty database produces empty array/CSV

test/integration/persistence.test.js — 5+ tests:
  - add tasks, create new Store instance, verify data persisted
  - modify task, reload, verify changes persisted
  - delete task, reload, verify deleted
  - corrupted data file (graceful error or reset)
  - data directory auto-created if missing

## Rules

1. Each test file is a SEPARATE subagent (8 subagents minimum)
2. After ALL implementations, run 'npm test'
3. If ANY test fails: fix the code, re-run tests. Repeat until ALL pass.
4. Do NOT mark DONE until npm test exits 0 with 50+ passing tests
5. Log test results to .claude/auto/taskman/test-results.md
6. Use gate checks: test suite must pass (gate 3), all files committed (gate 7)" \
    --plugin-dir "$PLUGIN_DIR" \
    --output-format stream-json \
    --verbose \
    > output.jsonl 2> errors.log

END_TS=$(date +%s)
ELAPSED=$((END_TS - START_TS))
echo ""
echo "End: $(date +%H:%M:%S)"
echo "WALL TIME: $((ELAPSED/60)) min $((ELAPSED%60)) sec"

# Results
echo ""
echo "=== Files ==="
find . -type f -not -path './.git/*' -not -path './node_modules/*' -not -name '*.jsonl' -not -name 'errors.log' | sort
echo ""
echo "=== Test files ==="
find test -name "*.test.js" 2>/dev/null
echo ""
echo "=== State ==="
for sf in $(find .claude/auto -name state.json -type f 2>/dev/null); do
    python3 -c "
import json; s=json.load(open('$sf'))
print(f'phase={s.get(\"phase\",\"?\")} status={s.get(\"status\",\"?\")}')
prog=s.get('progress',{})
if prog: print(f'  progress: tasks_passed={prog.get(\"tasks_passed\",0)}/{prog.get(\"tasks_total\",0)} gates_passed={prog.get(\"gates_passed\",0)}/{prog.get(\"gates_total\",0)}')
ts=s.get('task_states',{})
if ts:
    for tid,ti in sorted(ts.items()):
        if isinstance(ti,dict): print(f'  {tid}: {ti.get(\"status\",\"?\")}')
" 2>/dev/null
done
echo ""
echo "=== Token usage ==="
grep '"type":"result"' output.jsonl | python3 -c "
import json,sys
for l in sys.stdin:
    d=json.loads(l)
    if 'usage' in d:
        u=d['usage']
        print(f'input={u[\"input_tokens\"]} output={u[\"output_tokens\"]} cost=\${d.get(\"total_cost_usd\",0)}')
" 2>/dev/null
echo ""
echo "--- Summary ---"
echo "Wall: $((ELAPSED/60)) min $((ELAPSED%60)) sec"
echo "Files: $(find . -type f -not -path './.git/*' -not -path './node_modules/*' -not -name '*.jsonl' -not -name 'errors.log' | wc -l)"
echo "Tests: $(find test -name '*.test.js' 2>/dev/null | wc -l)"
report_failures
