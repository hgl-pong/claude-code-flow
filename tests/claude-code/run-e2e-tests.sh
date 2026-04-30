#!/usr/bin/env bash
# Run Claude Code Flow E2E tests.
#
# Fast tests (default): ask Claude to explain skills/commands; verify answers.
# Integration tests (--integration): execute a real plan end-to-end (10-30 min).
#
# Usage:
#   ./run-e2e-tests.sh                          # fast tests only
#   ./run-e2e-tests.sh --integration            # fast + integration
#   ./run-e2e-tests.sh --test test-skill-brainstorming.sh
#   ./run-e2e-tests.sh --verbose
#   ./run-e2e-tests.sh --timeout 600

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

TIMEOUT_SECONDS=240
SPECIFIC_TEST=""
VERBOSE=false
RUN_INTEGRATION=false

while [ $# -gt 0 ]; do
  case "$1" in
    --timeout)       TIMEOUT_SECONDS="$2"; shift 2 ;;
    --test)          SPECIFIC_TEST="$2";   shift 2 ;;
    --verbose|-v)    VERBOSE=true;         shift   ;;
    --integration|-i) RUN_INTEGRATION=true; shift  ;;
    --help|-h)
      cat <<HELP
Usage: $0 [options]

Options:
  --verbose, -v         Show full test output
  --test FILE           Run only the specified test file
  --timeout SECONDS     Per-test timeout (default: 240)
  --integration, -i     Also run slow integration tests (10-30 min each)
  --help, -h            Show this help

Fast tests (always run):
  test-workflow-skills.sh
  test-workflow-commands.sh
  test-local-regression-via-claude.sh
  test-skill-using-claude-code-flow.sh
  test-skill-brainstorming.sh
  test-skill-writing-plans.sh
  test-skill-testing-strategy.sh
  test-skill-systematic-debugging.sh
  test-skill-verification-before-completion.sh
  test-skill-dev-orchestrator.sh
  test-skill-uli.sh

Integration tests (--integration only):
  test-integration-dev-orchestrator.sh
  test-integration-uli.sh
HELP
      exit 0
      ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

cd "$ROOT_DIR"

echo "========================================"
echo " Claude Code Flow E2E Tests"
echo "========================================"
echo "Repository: $ROOT_DIR"
echo "Claude:     $(claude --version 2>/dev/null || echo 'not found')"
echo "Date:       $(date)"
echo ""

if ! command -v claude >/dev/null 2>&1; then
  echo "ERROR: Claude Code CLI not found in PATH." >&2
  exit 1
fi

# ------------------------------------------------------------------
# Preflight: verify Claude + model are available
# ------------------------------------------------------------------
if [ "${CLAUDE_E2E_SKIP_PREFLIGHT:-0}" != "1" ]; then
  preflight_output="$(mktemp)"
  set +e
  timeout 60 claude -p "Reply with exactly: OK" >"$preflight_output" 2>&1
  preflight_exit=$?
  set -e
  if [ "$preflight_exit" -ne 0 ]; then
    if [ "$preflight_exit" -eq 124 ] || [ ! -s "$preflight_output" ] || \
       grep -Eiq "API Error|ECONNRESET|Unable to connect|network error|ETIMEDOUT|ENOTFOUND" "$preflight_output"; then
      echo "SKIP: Claude Code CLI installed but model/API unavailable."
      cat "$preflight_output" | sed 's/^/  /'
      rm -f "$preflight_output"
      exit 0
    fi
    cat "$preflight_output" >&2
    rm -f "$preflight_output"
    exit 1
  fi
  if [ ! -s "$preflight_output" ]; then
    echo "SKIP: Claude Code preflight returned no output."
    rm -f "$preflight_output"
    exit 0
  fi
  rm -f "$preflight_output"
  echo "Preflight: OK"
  echo ""
fi

# ------------------------------------------------------------------
# Test lists
# ------------------------------------------------------------------
# Fast tests — ask Claude about skills/commands; verify its answers
fast_tests=(
  "test-workflow-skills.sh"
  "test-workflow-commands.sh"
  "test-local-regression-via-claude.sh"
  "test-skill-using-claude-code-flow.sh"
  "test-skill-brainstorming.sh"
  "test-skill-writing-plans.sh"
  "test-skill-testing-strategy.sh"
  "test-skill-systematic-debugging.sh"
  "test-skill-verification-before-completion.sh"
  "test-skill-dev-orchestrator.sh"
  "test-skill-uli.sh"
)

# Integration tests — actually execute a plan (slow, costs tokens)
integration_tests=(
  "test-integration-dev-orchestrator.sh"
  "test-integration-uli.sh"
)

tests=("${fast_tests[@]}")
[ "$RUN_INTEGRATION" = true ] && tests+=("${integration_tests[@]}")
[ -n "$SPECIFIC_TEST" ]       && tests=("$SPECIFIC_TEST")

# ------------------------------------------------------------------
# Run tests
# ------------------------------------------------------------------
passed=0; failed=0; skipped=0

run_one_test() {
  local test_name="$1"
  local test_path="$SCRIPT_DIR/$test_name"

  echo "----------------------------------------"
  echo "Running: $test_name"
  echo "----------------------------------------"

  if [ ! -f "$test_path" ]; then
    echo "  [FAIL] test file not found: $test_path"
    failed=$((failed+1))
    return
  fi

  if [ "$VERBOSE" = true ]; then
    if CLAUDE_E2E_TIMEOUT="$TIMEOUT_SECONDS" bash "$test_path"; then
      passed=$((passed+1))
    else
      local code=$?
      if [ "$code" -eq 77 ]; then
        echo "  [SKIP]"; skipped=$((skipped+1))
      else
        failed=$((failed+1))
      fi
    fi
  else
    if output="$(CLAUDE_E2E_TIMEOUT="$TIMEOUT_SECONDS" bash "$test_path" 2>&1)"; then
      echo "  [PASS]"
      passed=$((passed+1))
    else
      local code=$?
      if [ "$code" -eq 77 ]; then
        echo "  [SKIP]"
        printf '%s\n' "$output" | sed 's/^/    /'
        skipped=$((skipped+1))
      else
        echo "  [FAIL]"
        printf '%s\n' "$output" | sed 's/^/    /'
        failed=$((failed+1))
      fi
    fi
  fi
  echo ""
}

for t in "${tests[@]}"; do
  run_one_test "$t"
done

# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
echo "========================================"
echo " E2E Summary"
echo "========================================"
echo "Passed:  $passed"
echo "Failed:  $failed"
echo "Skipped: $skipped"
echo ""

if [ "$RUN_INTEGRATION" = false ] && [ ${#integration_tests[@]} -gt 0 ]; then
  echo "Note: integration tests were skipped (use --integration to run them)."
  echo ""
fi

[ "$failed" -gt 0 ] && exit 1 || exit 0
