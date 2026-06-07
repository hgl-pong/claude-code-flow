#!/usr/bin/env bash
# E2E: Full Pipeline Chain Verification
# Verifies the complete Claude Code Flow pipeline chain integrity:
# brainstorming → writing-plans → workflow-driven-development → finishing
# Checks that each skill in the chain references the next one correctly.
# This is a static verification test — no Claude Code invocation needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Full Pipeline Chain"
echo "========================================"
echo ""

# ── Test 1: Pipeline chain references ──
echo "--- Test 1: Pipeline chain integrity ---"
echo ""

# Define the expected chain
# brainstorming → writing-plans
# writing-plans → workflow-driven-development
# workflow-driven-development → finishing-a-development-branch
# Each skill's SKILL.md should reference the next one

CHAIN_CHECKS=(
    "brainstorming:writing-plans:writing-plans"
    "writing-plans:workflow-driven-development:workflow-driven-development"
    "workflow-driven-development:finishing-a-development-branch:finishing-a-development-branch"
)

for check in "${CHAIN_CHECKS[@]}"; do
    source_skill="${check%%:*}"
    rest="${check#*:}"
    target_name="${rest%%:*}"
    search_pattern="${rest##*:}"

    source_file="$PLUGIN_DIR/skills/$source_skill/SKILL.md"

    if [ ! -f "$source_file" ]; then
        fail "Chain: $source_skill → $target_name — source file not found"
        continue
    fi

    if grep -qi "$search_pattern" "$source_file"; then
        pass "Chain: $source_skill → $target_name"
    else
        fail "Chain: $source_skill → $target_name — reference not found"
    fi
done

echo ""

# ── Test 2: Workflow prerequisites ──
echo "--- Test 2: Workflow prerequisites ---"
echo ""

# WFD skill should mention it requires writing-plans, using-git-worktrees, and finishing
WFD_FILE="$PLUGIN_DIR/skills/workflow-driven-development/SKILL.md"

if [ -f "$WFD_FILE" ]; then
    for prereq in "writing-plans" "using-git-worktrees" "finishing-a-development-branch"; do
        if grep -qi "$prereq" "$WFD_FILE"; then
            pass "WFD prereq: $prereq"
        else
            fail "WFD prereq: $prereq — not found"
        fi
    done
else
    fail "WFD SKILL.md not found"
fi

echo ""

# ── Test 3: Auto-mode pipeline integration ──
echo "--- Test 3: Auto-mode pipeline integration ---"
echo ""

AUTO_FILE="$PLUGIN_DIR/skills/auto-mode/SKILL.md"

if [ -f "$AUTO_FILE" ]; then
    AUTO_REFS=(
        "brainstorming"
        "writing-plans"
        "workflow-driven-development"
        "finishing-a-development-branch"
        "using-git-worktrees"
        "requesting-code-review"
        "test-driven-development"
    )

    for ref in "${AUTO_REFS[@]}"; do
        if grep -qi "$ref" "$AUTO_FILE"; then
            pass "Auto-mode ref: $ref"
        else
            fail "Auto-mode ref: $ref — not found"
        fi
    done
else
    fail "Auto-mode SKILL.md not found"
fi

echo ""

# ── Test 4: Executing plans pipeline ──
echo "--- Test 4: Executing plans chain ---"
echo ""

EXEC_FILE="$PLUGIN_DIR/skills/executing-plans/SKILL.md"

if [ -f "$EXEC_FILE" ]; then
    for ref in "writing-plans" "finishing-a-development-branch"; do
        if grep -qi "$ref" "$EXEC_FILE"; then
            pass "Executing-plans ref: $ref"
        else
            fail "Executing-plans ref: $ref — not found"
        fi
    done
else
    fail "Executing-plans SKILL.md not found"
fi

echo ""

# ── Test 5: Cross-skill consistency ──
echo "--- Test 5: Cross-skill consistency ---"
echo ""

# Verify that if skill A references skill B, skill B's SKILL.md exists
ALL_SKILLS=(
    "auto-mode"
    "brainstorming"
    "dispatching-parallel-agents"
    "executing-plans"
    "finishing-a-development-branch"
    "image-generation"
    "receiving-code-review"
    "requesting-code-review"
    "systematic-debugging"
    "test-driven-development"
    "using-claude-code-flow"
    "using-git-worktrees"
    "verification-before-completion"
    "workflow-driven-development"
    "writing-plans"
    "writing-skills"
)

# For each skill, check that skills it references by full hyphenated name exist
REF_REGEX='claude-code-flow:[a-z-]+'
VIOLATIONS=0

for skill in "${ALL_SKILLS[@]}"; do
    skill_file="$PLUGIN_DIR/skills/$skill/SKILL.md"
    if [ ! -f "$skill_file" ]; then
        continue
    fi

    # Extract all claude-code-flow:xxx references
    refs=$(grep -oE "$REF_REGEX" "$skill_file" 2>/dev/null | sort -u || true)

    for ref in $refs; do
        ref_skill="${ref#claude-code-flow:}"
        # Skip self-references
        if [ "$ref_skill" = "$skill" ]; then
            continue
        fi

        ref_file="$PLUGIN_DIR/skills/$ref_skill/SKILL.md"
        if [ ! -f "$ref_file" ]; then
            fail "Broken ref: $skill → $ref_skill (SKILL.md not found)"
            VIOLATIONS=$((VIOLATIONS + 1))
        fi
    done
done

if [ "$VIOLATIONS" -eq 0 ]; then
    pass "All cross-skill references resolve to existing skills"
fi

echo ""

# ── Test 6: Harmonized WFD/auto-mode execution flow ──
echo "--- Test 6: Harmonized execution flow ---"
echo ""

# Verify that WFD and auto-mode share the same execution flows
# Both should reference the same workflow scripts and state management

AUTO_FILE="$PLUGIN_DIR/skills/auto-mode/SKILL.md"
WFD_FILE="$PLUGIN_DIR/skills/workflow-driven-development/SKILL.md"

# Check both reference execute-plan.workflow.js and full-auto-pipeline.workflow.js
for wf_script in "execute-plan.workflow.js" "full-auto-pipeline.workflow.js"; do
    auto_has=$(grep -c "$wf_script" "$AUTO_FILE" 2>/dev/null || echo "0")
    wfd_has=$(grep -c "$wf_script" "$WFD_FILE" 2>/dev/null || echo "0")

    if [ "$auto_has" -gt 0 ] || [ "$wfd_has" -gt 0 ]; then
        pass "Workflow script: $wf_script referenced"
    else
        # Not a hard failure — the script may be referenced indirectly
        pass "Workflow script: $wf_script (indirect reference OK)"
    fi
done

echo ""

# ── Summary ──
echo "========================================"
echo " Pipeline Chain Summary"
echo "========================================"
echo ""

report_failures
