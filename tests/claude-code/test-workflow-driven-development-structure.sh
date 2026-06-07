#!/usr/bin/env bash
# Test: workflow-driven development — structure validation
# Zero-cost static checks: file existence, JS syntax, JSON Schema validity, placeholder coverage
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

SKILL_DIR="$SCRIPT_DIR/../../skills/workflow-driven-development"

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

echo "Test 1b: SKILL.md contains Workflow-Driven Development title..."
if grep -q "Workflow-Driven Development" "$SKILL_DIR/SKILL.md"; then
    pass "SKILL.md has correct title"
else
    fail "SKILL.md missing Workflow-Driven Development title"
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

# Check meta block appears early (first non-comment, non-blank line)
if head -15 "$SKILL_DIR/execute-plan.workflow.js" | grep -q "export const meta"; then
    pass "export const meta appears in first 15 lines"
else
    fail "export const meta missing in first 15 lines"
    errors=$((errors + 1))
fi

# Check that workflow has a return statement at the end (modern pattern: return {...}
if grep -q "^return {" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "Has return statement (workflow result object)"
else
    fail "Missing return statement"
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

echo "Test 2d: Workflow script builds prompts inline..."
if grep -q "implementPrompt" "$SKILL_DIR/execute-plan.workflow.js" && \
   grep -q "specReviewPrompt" "$SKILL_DIR/execute-plan.workflow.js" && \
   grep -q "codeReviewPrompt" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "workflow script has inline prompt builder functions"
else
    fail "workflow script missing inline prompt builders"
fi

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

# ── Test 4: Behavioral content embedded in workflow script ────────────
echo "Test 4: Behavioral content in workflow script..."

if grep -q "Behavioral Guards" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "execute-plan.workflow.js embeds Behavioral Guards table"
else
    fail "execute-plan.workflow.js missing Behavioral Guards"
fi

if grep -q "Self-Review" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "execute-plan.workflow.js embeds Self-Review checklist"
else
    fail "execute-plan.workflow.js missing Self-Review"
fi

if grep -q "CRITICAL: Do Not Trust the Report" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "execute-plan.workflow.js embeds adversarial review stance"
else
    fail "execute-plan.workflow.js missing adversarial stance"
fi

if grep -q "When You're in Over Your Head" "$SKILL_DIR/execute-plan.workflow.js"; then
    pass "execute-plan.workflow.js embeds escalation guidance"
else
    fail "execute-plan.workflow.js missing escalation guidance"
fi

echo ""

# ── Test 5: Canonical prompt files unchanged ──────────────────────────
echo "Test 5: Canonical prompt files exist..."

ORIGINAL_FILES=(
    "implementer-prompt.md"
    "spec-reviewer-prompt.md"
    "code-quality-reviewer-prompt.md"
)

for file in "${ORIGINAL_FILES[@]}"; do
    if [ -f "$SKILL_DIR/$file" ]; then
        pass "$file exists"
    else
        fail "$file is missing"
    fi
done

echo "Test 5b: WF duplicates removed..."
for wf_file in "implementer-prompt-wf.md" "spec-reviewer-prompt-wf.md" "code-quality-reviewer-prompt-wf.md" "fix-prompt-wf.md"; do
    if [ ! -f "$SKILL_DIR/$wf_file" ]; then
        pass "$wf_file correctly removed (merged into workflow script)"
    else
        fail "$wf_file should not exist (content is now in workflow script)"
    fi
done

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
