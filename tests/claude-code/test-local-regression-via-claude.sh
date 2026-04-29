#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

timeout_seconds="${CLAUDE_E2E_TIMEOUT:-240}"

prompt='Run the local plugin regression test command `python tests/run-tests.py` in this repository. Do not edit files. Report the command and whether it passed.'

output="$(run_claude "$prompt" "$timeout_seconds" "Bash")"

assert_contains "$output" "python tests/run-tests.py" "reports local test command"
assert_contains "$output" "pass|passed|OK|success" "reports passing result"
assert_not_contains "$output" "fail|failed|error" "does not report failure"
