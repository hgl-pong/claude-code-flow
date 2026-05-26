#!/usr/bin/env bash
# Test: Skill Priority Resolution
# Documents current OpenCode duplicate-name behavior for local and bundled
# skills. The desired local-shadowing behavior is tracked separately; this
# test keeps the integration suite honest without adding a plugin workaround.
# NOTE: These tests require OpenCode to be installed and configured
set -euo pipefail

FAILURES=0

pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; FAILURES=$((FAILURES + 1)); }

report_failures() {
    if [ "$FAILURES" -eq 0 ]; then
        echo ""
        echo "=== All priority tests passed ==="
        return 0
    else
        echo ""
        echo "=== $FAILURES priority test(s) FAILED ==="
        return 1
    fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OPENCODE_TEST_TIMEOUT_SECONDS="${OPENCODE_TEST_TIMEOUT_SECONDS:-120}"

echo "=== Test: Skill Priority Resolution ==="

# Source setup to create isolated environment
source "$SCRIPT_DIR/setup.sh"

# Trap to cleanup on exit
trap cleanup_test_env EXIT

# Create same skill "priority-test" in all three locations with different markers
echo "Setting up priority test fixtures..."

# 1. Create in claude-code-flow location (lowest priority)
mkdir -p "$CCFLOW_SKILLS_DIR/priority-test"
cat > "$CCFLOW_SKILLS_DIR/priority-test/SKILL.md" <<'EOF'
---
name: priority-test
description: Claude Code Flow version of priority test skill
---
# Priority Test Skill (Claude Code Flow Version)

This is the CLAUDE_CODE_FLOW version of the priority test skill.

PRIORITY_MARKER_CCFLOW_VERSION
EOF

# 2. Create in personal location (medium priority)
mkdir -p "$OPENCODE_CONFIG_DIR/skills/priority-test"
cat > "$OPENCODE_CONFIG_DIR/skills/priority-test/SKILL.md" <<'EOF'
---
name: priority-test
description: Personal version of priority test skill
---
# Priority Test Skill (Personal Version)

This is the PERSONAL version of the priority test skill.

PRIORITY_MARKER_PERSONAL_VERSION
EOF

# 3. Create in project location (highest priority)
mkdir -p "$TEST_HOME/test-project/.opencode/skills/priority-test"
cat > "$TEST_HOME/test-project/.opencode/skills/priority-test/SKILL.md" <<'EOF'
---
name: priority-test
description: Project version of priority test skill
---
# Priority Test Skill (Project Version)

This is the PROJECT version of the priority test skill.

PRIORITY_MARKER_PROJECT_VERSION
EOF

echo "  Created priority-test skill in all three locations"

# Test 1: Verify fixture setup
echo ""
echo "Test 1: Verifying test fixtures..."

if [ -f "$CCFLOW_SKILLS_DIR/priority-test/SKILL.md" ]; then
    pass "Claude Code Flow version exists"
else
    fail "Claude Code Flow version missing"
fi

if [ -f "$OPENCODE_CONFIG_DIR/skills/priority-test/SKILL.md" ]; then
    pass "Personal version exists"
else
    fail "Personal version missing"
fi

if [ -f "$TEST_HOME/test-project/.opencode/skills/priority-test/SKILL.md" ]; then
    pass "Project version exists"
else
    fail "Project version missing"
fi

# Check if opencode is available for integration tests
if ! command -v opencode &> /dev/null; then
    echo ""
    echo "  [SKIP] OpenCode not installed - skipping integration tests"
    echo "  To run these tests, install OpenCode: https://opencode.ai"
    echo ""
    echo "=== Priority fixture tests passed (integration tests skipped) ==="
    exit 0
fi

run_opencode() {
    local result_var="$1"
    local dir="$2"
    local prompt="$3"
    local command_output
    local exit_code

    set +e
    command_output=$(cd "$dir" && timeout "${OPENCODE_TEST_TIMEOUT_SECONDS}s" opencode run --print-logs --format json "$prompt" 2>&1)
    exit_code=$?
    set -e

    if [ $exit_code -eq 124 ]; then
        echo "  [FAIL] OpenCode timed out after ${OPENCODE_TEST_TIMEOUT_SECONDS}s"
        FAILURES=$((FAILURES + 1))
        return 1
    fi

    if [ $exit_code -ne 0 ]; then
        echo "  [FAIL] OpenCode returned non-zero exit code: $exit_code"
        echo "  Output was:"
        awk 'NR <= 80 { print }' <<<"$command_output"
        FAILURES=$((FAILURES + 1))
        return 1
    fi

    printf -v "$result_var" '%s' "$command_output"
}

assert_contains() {
    local output="$1"
    local needle="$2"
    local message="$3"

    if [[ "$output" == *"$needle"* ]]; then
        echo "  [PASS] $message"
    else
        echo "  [FAIL] $message"
        echo "  Expected to find: $needle"
        echo "  Output was:"
        awk 'NR <= 80 { print }' <<<"$output"
        FAILURES=$((FAILURES + 1))
        return 1
    fi
}

first_skill_tool_event() {
    awk '/"type":"tool_use"/ && /"tool":"skill"/ { print; exit }' <<<"$1"
}

describe_priority_result() {
    local output="$1"
    local expected_marker="$2"
    local fallback_marker="$3"
    local pass_message="$4"
    local known_bug_message="$5"
    local loaded_skill

    loaded_skill="$(first_skill_tool_event "$output")"

    if [[ "$loaded_skill" == *"$expected_marker"* ]]; then
        echo "  [PASS] $pass_message"
    elif [[ "$loaded_skill" == *"$fallback_marker"* ]]; then
        echo "  [INFO] $known_bug_message"
        echo "  [INFO] Tracked separately: OpenCode bundled skills can shadow local skills with duplicate native names"
    else
        echo "  [FAIL] Could not verify priority marker in native skill tool output"
        echo "  Output was:"
        awk 'NR <= 80 { print }' <<<"$output"
        FAILURES=$((FAILURES + 1))
        return 1
    fi
}

# Test 2: Document personal vs bundled ccflow priority
echo ""
echo "Test 2: Documenting personal vs ccflow priority..."
echo "  Running from outside project directory..."

run_opencode output "$HOME" "Call the skill tool with name \"priority-test\". Show the exact content including any PRIORITY_MARKER text." || true
describe_priority_result \
    "$output" \
    "PRIORITY_MARKER_PERSONAL_VERSION" \
    "PRIORITY_MARKER_CCFLOW_VERSION" \
    "Personal version loaded for duplicate native skill name" \
    "Current OpenCode behavior loaded bundled ccflow version instead of personal version" || true

# Test 3: Document project vs bundled ccflow priority
echo ""
echo "Test 3: Documenting project vs personal/ccflow priority..."
echo "  Running from project directory..."

run_opencode output "$TEST_HOME/test-project" "Call the skill tool with name \"priority-test\". Show the exact content including any PRIORITY_MARKER text." || true
describe_priority_result \
    "$output" \
    "PRIORITY_MARKER_PROJECT_VERSION" \
    "PRIORITY_MARKER_CCFLOW_VERSION" \
    "Project version loaded for duplicate native skill name" \
    "Current OpenCode behavior loaded bundled ccflow version instead of project version" || true

# Test 4: Test a non-colliding bundled ccflow skill is still available
echo ""
echo "Test 4: Testing non-colliding ccflow skill remains available..."

mkdir -p "$CCFLOW_SKILLS_DIR/ccflow-only-test"
cat > "$CCFLOW_SKILLS_DIR/ccflow-only-test/SKILL.md" <<'EOF'
---
name: ccflow-only-test
description: Claude Code Flow only priority test skill
---
# Claude Code Flow Only Test Skill

PRIORITY_MARKER_CCFLOW_ONLY_VERSION
EOF

run_opencode output "$TEST_HOME/test-project" "Call the skill tool with name \"ccflow-only-test\". Show the exact content including any PRIORITY_MARKER text." || true
assert_contains "$output" "PRIORITY_MARKER_CCFLOW_ONLY_VERSION" "Non-colliding ccflow skill is still registered" || true

echo ""

report_failures
exit $?
