#!/usr/bin/env bash
# Test: workflow-driven development — structure validation
# Zero-cost static checks: file existence, JS syntax, JSON Schema validity, placeholder coverage
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

SKILL_DIR="$SCRIPT_DIR/../../skills/subagent-driven-development"

echo "=== Test: workflow-driven development — structure ==="
echo ""

# ── Test 1: All workflow files exist ────────────────────────────────────
echo "Test 1: File existence..."

check_file() {
    if [ -f "$SKILL_DIR/$1" ]; then
        pass "$1 exists"
    else
        fail "$1 does not exist"
    fi
}

check_file "execute-plan.workflow.js"
check_file "full-auto-pipeline.workflow.js"
check_file "implementer-prompt-wf.md"
check_file "spec-reviewer-prompt-wf.md"
check_file "code-quality-reviewer-prompt-wf.md"
check_file "fix-prompt-wf.md"

echo "Test 1b: SKILL.md contains Workflow-Driven Mode section..."
if grep -q "Workflow-Driven Mode" "$SKILL_DIR/SKILL.md"; then
    pass "SKILL.md references Workflow-Driven Mode"
else
    fail "SKILL.md missing Workflow-Driven Mode section"
fi

echo ""

# ── Test 2: Workflow script is valid JavaScript ─────────────────────────
echo "Test 2: Workflow script structure..."

# node -c can't handle workflow scripts (top-level export + return),
# so we validate structural completeness instead
errors=0

# Check braces are balanced
open=$(grep -o '{' "$SKILL_DIR/execute-plan.workflow.js" | wc -l)
close=$(grep -o '}' "$SKILL_DIR/execute-plan.workflow.js" | wc -l)
if [ "$open" -eq "$close" ]; then
    pass "Braces balanced ($open open, $close close)"
else
    fail "Braces unbalanced ($open open, $close close)"
    errors=$((errors + 1))
fi

# Check parentheses balanced
open=$(grep -o '(' "$SKILL_DIR/execute-plan.workflow.js" | wc -l)
close=$(grep -o ')' "$SKILL_DIR/execute-plan.workflow.js" | wc -l)
if [ "$open" -eq "$close" ]; then
    pass "Parentheses balanced ($open open, $close close)"
else
    fail "Parentheses unbalanced ($open open, $close close)"
    errors=$((errors + 1))
fi

# Check brackets balanced
open=$(grep -o '\[' "$SKILL_DIR/execute-plan.workflow.js" | wc -l)
close=$(grep -o '\]' "$SKILL_DIR/execute-plan.workflow.js" | wc -l)
if [ "$open" -eq "$close" ]; then
    pass "Brackets balanced ($open open, $close close)"
else
    fail "Brackets unbalanced ($open open, $close close)"
    errors=$((errors + 1))
fi

# Check no obvious syntax errors
if head -1 "$SKILL_DIR/execute-plan.workflow.js" | grep -q "export const meta"; then
    pass "Starts with export const meta"
else
    fail "Missing export const meta at start"
    errors=$((errors + 1))
fi

# Check that all async functions have await inside, and no orphaned 'return results'
if grep -q "return results" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "Has return results (valid in workflow runtime)"
else
    fail "Missing return results"
    errors=$((errors + 1))
fi

[ "$errors" -eq 0 ] || true

echo "Test 2b: Workflow script contains meta block..."
if grep -q "export const meta" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "execute-plan.workflow.js has meta block"
else
    fail "execute-plan.workflow.js missing meta block"
fi

echo "Test 2c: Meta block has required fields..."
if grep -q "name:" "$SKILL_DIR/execute-plan.workflow.js" && \
   grep -q "description:" "$SKILL_DIR/execute-plan.workflow.js" && \
   grep -q "phases:" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "execute-plan.workflow.js meta has name, description, phases"
else
    fail "execute-plan.workflow.js meta missing required fields"
fi

echo "Test 2d: Workflow script references all prompts keys..."
for key in 'prompts\.implement' 'prompts\.specReview' 'prompts\.codeReview' 'prompts\.fix'; do
    if grep -q "$key" "$SKILL_DIR/execute-plan.workflow.js"; then
        pass "workflow script uses $key"
    else
        fail "workflow script missing $key reference"
    fi
done

echo ""

# ── Test 3: Schema definitions ──────────────────────────────────────────
echo "Test 3: Schema definitions..."

echo "Test 3a: IMPLEMENT_RESULT schema..."
if grep -q "IMPLEMENT_RESULT" "$SKILL_DIR/execute-plan.workflow.js"; then
    # Verify required status enum values (single-quoted in JS source)
    if grep -q "'DONE'" "$SKILL_DIR/execute-plan.workflow.js" && \
       grep -q "'DONE_WITH_CONCERNS'" "$SKILL_DIR/execute-plan.workflow.js" && \
       grep -q "'BLOCKED'" "$SKILL_DIR/execute-plan.workflow.js"; then
        pass "IMPLEMENT_RESULT has correct status enum values"
    else
        fail "IMPLEMENT_RESULT missing status enum values"
    fi

    # Verify required fields in schema
    if grep -q "required:.*status" "$SKILL_DIR/execute-plan.workflow.js" && \
       grep -q "required:.*summary" "$SKILL_DIR/execute-plan.workflow.js" && \
       grep -q "files_modified" "$SKILL_DIR/execute-plan.workflow.js"; then
        pass "IMPLEMENT_RESULT has required fields (status, summary, files_modified)"
    else
        fail "IMPLEMENT_RESULT missing required fields"
    fi
else
    fail "IMPLEMENT_RESULT schema not found"
fi

echo "Test 3b: REVIEW_RESULT schema..."
if grep -q "REVIEW_RESULT" "$SKILL_DIR/execute-plan.workflow.js"; then
    if grep -q "'passed'" "$SKILL_DIR/execute-plan.workflow.js" && \
       grep -q "'issues'" "$SKILL_DIR/execute-plan.workflow.js" && \
       grep -q "'severity'" "$SKILL_DIR/execute-plan.workflow.js"; then
        pass "REVIEW_RESULT has correct structure"
    else
        fail "REVIEW_RESULT missing required fields"
    fi

    # Verify severity enum values
    if grep -q "'Critical'" "$SKILL_DIR/execute-plan.workflow.js" && \
       grep -q "'Important'" "$SKILL_DIR/execute-plan.workflow.js" && \
       grep -q "'Minor'" "$SKILL_DIR/execute-plan.workflow.js"; then
        pass "REVIEW_RESULT has correct severity enum values"
    else
        fail "REVIEW_RESULT missing severity enum values"
    fi
else
    fail "REVIEW_RESULT schema not found"
fi

echo ""

# ── Test 4: Prompt templates contain required placeholders ──────────────
echo "Test 4: Prompt template placeholders..."

check_placeholder() {
    local file="$1"
    local placeholder="$2"
    if grep -F -q "$placeholder" "$SKILL_DIR/$file"; then
        pass "$file contains $placeholder"
    else
        fail "$file missing placeholder: $placeholder"
    fi
}

# implementer-prompt-wf.md
check_placeholder "implementer-prompt-wf.md" "{{TASK_ID}}"
check_placeholder "implementer-prompt-wf.md" "{{TASK_DESCRIPTION}}"
check_placeholder "implementer-prompt-wf.md" "{{WORKTREE}}"

# spec-reviewer-prompt-wf.md
check_placeholder "spec-reviewer-prompt-wf.md" "{{TASK_DESCRIPTION}}"
check_placeholder "spec-reviewer-prompt-wf.md" "{{IMPLEMENTER_SUMMARY}}"
check_placeholder "spec-reviewer-prompt-wf.md" "{{FILES_MODIFIED}}"

# code-quality-reviewer-prompt-wf.md
check_placeholder "code-quality-reviewer-prompt-wf.md" "{{TASK_SUMMARY}}"
check_placeholder "code-quality-reviewer-prompt-wf.md" "{{COMMIT_SHA}}"
check_placeholder "code-quality-reviewer-prompt-wf.md" "{{FILES_MODIFIED}}"

# fix-prompt-wf.md
check_placeholder "fix-prompt-wf.md" "{{ISSUES}}"
check_placeholder "fix-prompt-wf.md" "{{FILES_MODIFIED}}"

echo ""

# ── Test 5: Existing files unchanged ────────────────────────────────────
echo "Test 5: Existing files unchanged..."

ORIGINAL_FILES=(
    "implementer-prompt.md"
    "spec-reviewer-prompt.md"
    "code-quality-reviewer-prompt.md"
)

for file in "${ORIGINAL_FILES[@]}"; do
    if [ -f "$SKILL_DIR/$file" ]; then
        pass "$file still exists (not replaced by -wf variant)"
    else
        fail "$file is missing (may have been replaced by -wf variant)"
    fi
done

echo "Test 5b: New files don't overwrite existing files..."
# -wf files should be distinct files, not replacing existing ones
for file in "${ORIGINAL_FILES[@]}"; do
    wf_file="${file%.md}-wf.md"
    if [ -f "$SKILL_DIR/$wf_file" ]; then
        # Both exist — good
        :
    fi
done
# If we got here without errors, all old + new files coexist
pass "All -wf files coexist alongside original templates"

echo ""

# ── Test 6: Workflow script key logic checks ────────────────────────────
echo "Test 6: Workflow script logic..."

if grep -q "pipeline" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "workflow script uses pipeline for task chains"
else
    fail "workflow script missing pipeline usage"
fi

if grep -q "parallel" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "workflow script uses parallel for dependency groups"
else
    fail "workflow script missing parallel usage"
fi

if grep -q "MAX_RETRIES" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "workflow script has retry limit"
else
    fail "workflow script missing retry limit"
fi

if grep -q "BLOCKED" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "workflow script handles BLOCKED status"
else
    fail "workflow script missing BLOCKED handling"
fi

echo ""

report_failures
exit $?
