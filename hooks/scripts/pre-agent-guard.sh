#!/bin/bash
# PreToolUse(Agent): validate orchestration context before spawning agents
INPUT=$(cat)
FLOW_DIR=".claude/flow"
LOG_EVENT_SCRIPT="$(dirname "$0")/log-event.py"

has_flow_modified_files() {
  [ -f "$FLOW_DIR/modified-files.jsonl" ] && [ -s "$FLOW_DIR/modified-files.jsonl" ]
}

has_git_changes() {
  git status --short 2>/dev/null | grep -q .
}

has_explicit_review_target() {
  echo "$INPUT" | grep -Eqi \
    'review_focus|document_quality|spec_compliance|code_quality|Files to review|File Scope|diff summary|target files|relevant diff|--docs|--diff|\.claude/flow|([[:alnum:]_.-]+/)+[[:alnum:]_.-]*|[[:alnum:]_.\/-]+\.(py|js|ts|tsx|jsx|md|json|ya?ml|sh|toml|css|scss|html|go|rs|java|kt|cs|cpp|c|h|hpp|txt|diff|patch)'
}

# Only check sentinel — all other agents can proceed freely
if echo "$INPUT" | grep -qi 'sentinel'; then
  if ! has_flow_modified_files && ! has_git_changes && ! has_explicit_review_target; then
    python "$LOG_EVENT_SCRIPT" tool_guard_block "guard=pre-agent" "agent=sentinel" "reason=no_review_target" 2>/dev/null || true
    echo '{"decision":"block","reason":"No review target found. Provide files, diff/context, document review_focus, or run implementation first."}' >&2
    exit 2
  fi
fi

exit 0
