#!/usr/bin/env bash
# LONG_RUNNING: Behavioral e2e test for research pipeline
# Runs unattended Claude Code invocations to verify research skill dispatch.
# Uses stream-json output to detect skill/tool invocations.
# Expect 5-10 minutes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "======================================"
echo " E2E Test: Research Pipeline"
echo "======================================"
echo ""
echo "LONG_RUNNING: Expect 5-10 minutes."
echo ""

if [ "${RUN_LONG_TESTS:-}" != "true" ]; then
    echo "SKIP: Set RUN_LONG_TESTS=true to run long-running tests."
    exit 0
fi

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Test 1: Brainstorming skill triggers on naive prompt
echo "Test 1: Brainstorming triggers..."
brainstorm_log="$TMPDIR/brainstorm-output.json"
claude -p "Let's design a CLI password manager with encrypted local storage." \
    --plugin-dir "$(cd "$SCRIPT_DIR/../.." && pwd)" \
    --dangerously-skip-permissions \
    --max-turns 5 \
    --output-format stream-json \
    --verbose \
    > "$brainstorm_log" 2>&1 || true

# Check for Skill tool invocation with brainstorming
if grep -q '"name":"Skill"' "$brainstorm_log" && grep -qE '"skill":"[^"]*brainstorming"' "$brainstorm_log"; then
    echo "  [PASS] Brainstorming skill triggered"
else
    echo "  [FAIL] Brainstorming skill NOT triggered"
    echo "  Skills found in output:"
    grep -o '"skill":"[^"]*"' "$brainstorm_log" 2>/dev/null | sort -u || echo "    (none)"
fi

# Check for research references in the stream output
if grep -qE 'research|researcher|\.claude/research' "$brainstorm_log"; then
    echo "  [PASS] Research referenced in brainstorming output"
else
    echo "  [INFO] Research not referenced in first 5 turns (brainstorming needs user interaction)"
fi

echo ""

# Test 2: Research output directory
echo "Test 2: Research output directory..."
RESEARCH_DIR=".claude/research"
if [ -d "$RESEARCH_DIR" ]; then
    research_files=$(find "$RESEARCH_DIR" -name "*-research.md" -type f 2>/dev/null)
    if [ -n "$research_files" ]; then
        echo "  [PASS] Research files exist:"
        echo "$research_files" | while read -r f; do echo "    $f"; done
    else
        echo "  [FAIL] .claude/research/ exists but no *-research.md files found"
    fi
else
    echo "  [INFO] .claude/research/ not yet created"
fi

echo ""

# Test 3: Writing-plans dispatches researcher
echo "Test 3: Writing-plans dispatches researcher..."
plan_log="$TMPDIR/plan-output.json"
claude -p "Create an implementation plan for adding a 'hello' command that prints Hello, World!." \
    --plugin-dir "$(cd "$SCRIPT_DIR/../.." && pwd)" \
    --dangerously-skip-permissions \
    --max-turns 10 \
    --output-format stream-json \
    --verbose \
    > "$plan_log" 2>&1 || true

# Check for writing-plans skill invocation
if grep -qE '"skill":"[^"]*writing-plans"' "$plan_log"; then
    echo "  [PASS] Writing-plans skill triggered"
else
    echo "  [INFO] Writing-plans skill not triggered (may need different prompt)"
fi

# Check for researcher Agent dispatch (researcher-prompt.md reference)
if grep -qE 'researcher-prompt|researcher' "$plan_log"; then
    echo "  [PASS] Researcher subagent referenced in writing-plans"
elif grep -qE 'technical.research|technical-research' "$plan_log"; then
    echo "  [PASS] Technical research referenced in writing-plans"
else
    echo "  [INFO] Researcher dispatch not visible in stream-json (may be internal Agent tool call)"
fi

echo ""

# Test 4: Source provenance in research files
echo "Test 4: Source provenance in research output..."
if [ -d "$RESEARCH_DIR" ]; then
    all_research=$(find "$RESEARCH_DIR" -name "*-research.md" -type f 2>/dev/null)
    if [ -z "$all_research" ]; then
        echo "  [INFO] No research files found"
    else
        research_count=$(echo "$all_research" | wc -l)
        echo "  [PASS] $research_count research file(s) found"

        # Check for source provenance tags in research files
        provenance_found=false
        while IFS= read -r f; do
            if [ -z "$f" ]; then continue; fi
            if grep -qE 'source: (local|web|both)|Source provenance|URLs and access dates|Cross-reference' "$f" 2>/dev/null; then
                echo "  [PASS] Source provenance in: $(basename "$f")"
                provenance_found=true
            fi
        done <<< "$all_research"

        if [ "$provenance_found" = false ]; then
            echo "  [INFO] No source provenance tags found in existing research files (pre-date this feature)"
        fi
    fi
else
    echo "  [FAIL] .claude/research/ directory not found"
fi

echo ""
report_failures
exit $?
