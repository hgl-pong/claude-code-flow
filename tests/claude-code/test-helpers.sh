#!/usr/bin/env bash
# Helper functions for Claude Code E2E tests.

set -euo pipefail

is_claude_infra_failure() {
  local file="$1"
  grep -Eiq "API Error|ECONNRESET|Unable to connect|network error|ETIMEDOUT|ENOTFOUND" "$file"
}

run_claude() {
  local prompt="$1"
  local timeout_seconds="${2:-120}"
  local allowed_tools="${3:-}"
  local output_file
  output_file="$(mktemp)"

  local cmd=(claude -p "$prompt")
  if [ -n "$allowed_tools" ]; then
    cmd+=(--allowed-tools="$allowed_tools")
  fi

  if timeout "$timeout_seconds" "${cmd[@]}" >"$output_file" 2>&1; then
    if [ ! -s "$output_file" ] || is_claude_infra_failure "$output_file"; then
      echo "SKIP: Claude Code returned no usable model output." >&2
      cat "$output_file" >&2
      rm -f "$output_file"
      return 77
    fi
    cat "$output_file"
    rm -f "$output_file"
    return 0
  fi

  local exit_code=$?
  if is_claude_infra_failure "$output_file"; then
    echo "SKIP: Claude Code model/API unavailable." >&2
    cat "$output_file" >&2
    rm -f "$output_file"
    return 77
  fi

  cat "$output_file" >&2
  rm -f "$output_file"
  return "$exit_code"
}

assert_contains() {
  local output="$1"
  local pattern="$2"
  local name="${3:-assert_contains}"

  if printf '%s\n' "$output" | grep -Eiq "$pattern"; then
    echo "  [PASS] $name"
    return 0
  fi

  echo "  [FAIL] $name"
  echo "  Expected pattern: $pattern"
  echo "  Output:"
  printf '%s\n' "$output" | sed 's/^/    /'
  return 1
}

assert_not_contains() {
  local output="$1"
  local pattern="$2"
  local name="${3:-assert_not_contains}"

  if printf '%s\n' "$output" | grep -Eiq "$pattern"; then
    echo "  [FAIL] $name"
    echo "  Unexpected pattern: $pattern"
    echo "  Output:"
    printf '%s\n' "$output" | sed 's/^/    /'
    return 1
  fi

  echo "  [PASS] $name"
}

assert_order() {
  local output="$1"
  local first="$2"
  local second="$3"
  local name="${4:-assert_order}"

  local first_line
  local second_line
  first_line="$(printf '%s\n' "$output" | grep -Ein "$first" | head -1 | cut -d: -f1 || true)"
  second_line="$(printf '%s\n' "$output" | grep -Ein "$second" | head -1 | cut -d: -f1 || true)"

  if [ -z "$first_line" ] || [ -z "$second_line" ]; then
    echo "  [FAIL] $name"
    echo "  Missing order pattern(s): $first / $second"
    printf '%s\n' "$output" | sed 's/^/    /'
    return 1
  fi

  if [ "$first_line" -lt "$second_line" ]; then
    echo "  [PASS] $name"
    return 0
  fi

  echo "  [FAIL] $name"
  echo "  Expected '$first' before '$second'"
  printf '%s\n' "$output" | sed 's/^/    /'
  return 1
}
