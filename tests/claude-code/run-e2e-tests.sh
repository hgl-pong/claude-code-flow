#!/usr/bin/env bash
# Run Claude Code E2E tests.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

TIMEOUT_SECONDS=240
SPECIFIC_TEST=""
VERBOSE=false

while [ $# -gt 0 ]; do
  case "$1" in
    --timeout)
      TIMEOUT_SECONDS="$2"
      shift 2
      ;;
    --test)
      SPECIFIC_TEST="$2"
      shift 2
      ;;
    --verbose|-v)
      VERBOSE=true
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [--timeout seconds] [--test test-file] [--verbose]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

cd "$ROOT_DIR"

echo "========================================"
echo " Claude Code Flow E2E Tests"
echo "========================================"
echo "Repository: $ROOT_DIR"
echo "Claude: $(claude --version 2>/dev/null || echo 'not found')"
echo ""

if ! command -v claude >/dev/null 2>&1; then
  echo "ERROR: Claude Code CLI not found in PATH." >&2
  exit 1
fi

if [ "${CLAUDE_E2E_SKIP_PREFLIGHT:-0}" != "1" ]; then
  preflight_output="$(mktemp)"
  set +e
  timeout 60 claude -p "Reply with exactly: OK" >"$preflight_output" 2>&1
  preflight_exit=$?
  set -e
  if [ "$preflight_exit" -ne 0 ]; then
    if [ "$preflight_exit" -eq 124 ] || [ ! -s "$preflight_output" ] || grep -Eiq "API Error|ECONNRESET|Unable to connect|network error|ETIMEDOUT|ENOTFOUND" "$preflight_output"; then
      echo "SKIP: Claude Code CLI is installed, but the model/API is unavailable right now."
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
fi

tests=(
  "test-workflow-skills.sh"
  "test-workflow-commands.sh"
  "test-local-regression-via-claude.sh"
)

if [ -n "$SPECIFIC_TEST" ]; then
  tests=("$SPECIFIC_TEST")
fi

passed=0
failed=0
skipped=0

for test_name in "${tests[@]}"; do
  test_path="$SCRIPT_DIR/$test_name"
  echo "----------------------------------------"
  echo "Running: $test_name"
  echo "----------------------------------------"

  if [ ! -f "$test_path" ]; then
    echo "  [FAIL] missing test: $test_path"
    failed=$((failed + 1))
    continue
  fi

  if [ "$VERBOSE" = true ]; then
    if CLAUDE_E2E_TIMEOUT="$TIMEOUT_SECONDS" bash "$test_path"; then
      passed=$((passed + 1))
    else
      exit_code=$?
      if [ "$exit_code" -eq 77 ]; then
        echo "  [SKIP]"
        skipped=$((skipped + 1))
      else
        failed=$((failed + 1))
      fi
    fi
  else
    if output="$(CLAUDE_E2E_TIMEOUT="$TIMEOUT_SECONDS" bash "$test_path" 2>&1)"; then
      echo "  [PASS]"
      passed=$((passed + 1))
    else
      exit_code=$?
      if [ "$exit_code" -eq 77 ]; then
        echo "  [SKIP]"
        printf '%s\n' "$output" | sed 's/^/    /'
        skipped=$((skipped + 1))
      else
        echo "  [FAIL]"
        printf '%s\n' "$output" | sed 's/^/    /'
        failed=$((failed + 1))
      fi
    fi
  fi
  echo ""
done

echo "========================================"
echo "E2E Summary"
echo "========================================"
echo "Passed: $passed"
echo "Failed: $failed"
echo "Skipped: $skipped"

if [ "$failed" -gt 0 ]; then
  exit 1
fi
