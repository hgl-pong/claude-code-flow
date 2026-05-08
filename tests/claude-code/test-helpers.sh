#!/usr/bin/env bash
# Helper functions for Claude Code E2E tests.
# Helper functions modelled on common Claude Code plugin test patterns.

set -euo pipefail

# ---------------------------------------------------------------------------
# Infrastructure helpers
# ---------------------------------------------------------------------------

is_claude_infra_failure() {
  local file="$1"
  grep -Eiq "API Error|ECONNRESET|Unable to connect|network error|ETIMEDOUT|ENOTFOUND" "$file"
}

# Run Claude Code in headless (-p) mode and return its stdout.
# Returns 77 (SKIP) when the model/API is unavailable.
# Usage: run_claude "prompt" [timeout_seconds] [allowed_tools] [extra_flags...]
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
  # Forward any extra flags passed as $4 $5 …
  shift 3 2>/dev/null || true
  cmd+=("$@")

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

# Run Claude and capture output to a named file for later transcript analysis.
# Usage: run_claude_to_file "prompt" output_file [timeout] [allowed_tools] [extra_flags...]
run_claude_to_file() {
  local prompt="$1"
  local output_file="$2"
  local timeout_seconds="${3:-300}"
  local allowed_tools="${4:-}"
  shift 4 2>/dev/null || true

  local cmd=(claude -p "$prompt")
  if [ -n "$allowed_tools" ]; then
    cmd+=(--allowed-tools="$allowed_tools")
  fi
  cmd+=("$@")

  timeout "$timeout_seconds" "${cmd[@]}" >"$output_file" 2>&1
}

# ---------------------------------------------------------------------------
# Project / fixture helpers
# ---------------------------------------------------------------------------

# Create a temporary test project directory and echo its path.
create_test_project() {
  mktemp -d
}

# Remove a test project directory.
cleanup_test_project() {
  local dir="$1"
  [ -d "$dir" ] && rm -rf "$dir"
}

# Write a minimal Node.js package.json (ESM) into a directory.
init_node_project() {
  local dir="$1"
  cat >"$dir/package.json" <<'PKGJSON'
{
  "name": "test-project",
  "version": "1.0.0",
  "type": "module",
  "scripts": { "test": "node --test" }
}
PKGJSON
  mkdir -p "$dir/src" "$dir/test"
}

# Initialise a bare git repo inside a directory with an initial commit.
init_git_repo() {
  local dir="$1"
  git -C "$dir" init --quiet
  git -C "$dir" config user.email "test@example.com"
  git -C "$dir" config user.name "Test User"
  git -C "$dir" add .
  git -C "$dir" commit -m "Initial commit" --quiet
}

# Create a minimal claude-code-flow plan file.
# Usage: create_test_plan <project_dir> [plan_filename]
create_test_plan() {
  local dir="$1"
  local name="${2:-test-plan}"
  local plan_file="$dir/docs/plans/$name.md"
  mkdir -p "$(dirname "$plan_file")"
  cat >"$plan_file" <<'PLAN'
# Test Implementation Plan

## Task 1: Create Add Function

Create a function that adds two numbers.

**File:** `src/math.js`
**Requirements:**
- Export function named `add(a, b)` returning `a + b`

**Tests:** `test/math.test.js` — verify add(2,3)=5, add(0,0)=0, add(-1,1)=0
**Verification:** `npm test`

## Task 2: Create Multiply Function

Add a multiply function to `src/math.js`.

**Requirements:**
- Export function named `multiply(a, b)` returning `a * b`
- Do NOT add divide, subtract, or power functions

**Tests:** add to `test/math.test.js` — verify multiply(2,3)=6, multiply(0,5)=0
**Verification:** `npm test`
PLAN
  echo "$plan_file"
}

# Find the most-recently-modified Claude session JSONL for a given working dir.
# Usage: find_session_file "/abs/path/to/working/dir" [max_age_minutes]
find_session_file() {
  local working_dir="$1"
  local max_age="${2:-60}"
  # Claude encodes the working dir path as the project subdir name
  local encoded
  encoded="$(printf '%s' "$working_dir" | sed 's|/|-|g' | sed 's|^-||')"
  local session_dir="$HOME/.claude/projects/$encoded"
  find "$session_dir" -name "*.jsonl" -type f -mmin "-$max_age" 2>/dev/null \
    | sort -r | head -1
}

# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

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

  local first_line second_line
  first_line="$(printf '%s\n' "$output" | grep -Ein "$first"  | head -1 | cut -d: -f1 || true)"
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

# Verify that a grep pattern matches exactly N times.
# Usage: assert_count "output" "pattern" expected_count "test name"
assert_count() {
  local output="$1"
  local pattern="$2"
  local expected="$3"
  local name="${4:-assert_count}"

  local actual
  actual="$(printf '%s\n' "$output" | grep -Eic "$pattern" || echo 0)"

  if [ "$actual" -eq "$expected" ]; then
    echo "  [PASS] $name (found $actual)"
    return 0
  fi

  echo "  [FAIL] $name"
  echo "  Expected $expected occurrences of: $pattern"
  echo "  Found: $actual"
  printf '%s\n' "$output" | sed 's/^/    /'
  return 1
}

# Assert that a file exists.
assert_file_exists() {
  local path="$1"
  local name="${2:-file exists: $path}"
  if [ -f "$path" ]; then
    echo "  [PASS] $name"
    return 0
  fi
  echo "  [FAIL] $name (not found: $path)"
  return 1
}

# Assert that a file contains a pattern.
assert_file_contains() {
  local path="$1"
  local pattern="$2"
  local name="${3:-file contains: $pattern}"
  if grep -Eiq "$pattern" "$path" 2>/dev/null; then
    echo "  [PASS] $name"
    return 0
  fi
  echo "  [FAIL] $name"
  echo "  Pattern not found in $path: $pattern"
  return 1
}

# Assert that a JSONL session file contains a tool invocation.
# Usage: assert_session_tool "session.jsonl" "ToolName" "test name"
assert_session_tool() {
  local session_file="$1"
  local tool_name="$2"
  local name="${3:-session uses $tool_name}"
  if grep -q "\"name\":\"$tool_name\"" "$session_file" 2>/dev/null; then
    echo "  [PASS] $name"
    return 0
  fi
  echo "  [FAIL] $name (tool '$tool_name' not found in session)"
  return 1
}

# Assert that a JSONL session file invoked a specific Skill.
# Matches both "skill":"name" and "skill":"namespace:name".
# Usage: assert_session_skill "session.jsonl" "skill-name" "test name"
assert_session_skill() {
  local session_file="$1"
  local skill_name="$2"
  local name="${3:-session invokes skill: $skill_name}"
  local pattern="\"skill\":\"([^\"]*:)?${skill_name}\""
  if grep -Eq "$pattern" "$session_file" 2>/dev/null; then
    echo "  [PASS] $name"
    return 0
  fi
  echo "  [FAIL] $name (skill '$skill_name' not invoked in session)"
  return 1
}
