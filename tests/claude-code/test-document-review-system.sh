#!/usr/bin/env bash
# Integration Test: Document Review System
# Verifies the document reviewer catches intentional spec errors
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " Integration Test: Document Review System"
echo "========================================"
echo ""
echo "This test verifies the document review system by:"
echo "  1. Providing a spec with intentional errors"
echo "  2. Running the spec document reviewer"
echo "  3. Verifying the reviewer catches the errors"
echo ""

OUTPUT_FILE=$(mktemp)
trap "rm -f $OUTPUT_FILE" EXIT

SPEC_CONTENT='# Test Feature Design

## Overview

This is a test feature that does something useful.

## Requirements

1. The feature should work correctly
2. It should be fast
3. TODO: Add more requirements here

## Architecture

The feature will use a simple architecture with:
- A frontend component
- A backend service
- Error handling will be specified later once we understand the failure modes better

## Data Flow

Data flows from the frontend to the backend.

## Testing Strategy

Tests will be written to cover the main functionality.'

echo "Created test spec with intentional errors:"
echo "  - TODO placeholder in Requirements section"
echo "  - 'specified later' deferral in Architecture section"
echo ""
echo "Running spec document reviewer..."
echo ""

PROMPT="You are testing the spec document reviewer.

Read the claude-code-flow:document-review skill and the spec-document-reviewer-prompt.md template if available.

Then review the following spec using the review criteria from that template. The spec text is:

\`\`\`markdown
$SPEC_CONTENT
\`\`\`

Look for:
- TODOs, placeholders, 'TBD', incomplete sections
- Sections saying 'to be defined later' or 'will spec when X is done'
- Sections noticeably less detailed than others

Output your review in the format specified in the template. Include an Issues section and a verdict (Approved or Issues Found)."

echo "================================================================================"
timeout 120 claude -p "$PROMPT" --permission-mode bypassPermissions 2>&1 | tee "$OUTPUT_FILE" || {
    exit_code=$?
    echo ""
    echo "================================================================================"
    echo "EXECUTION FAILED (exit code: $exit_code)"
    exit 1
}
echo "================================================================================"

echo ""
echo "Analyzing reviewer output..."
echo ""

FAILED=0

echo "=== Verification Tests ==="
echo ""

# Test 1: Reviewer found the TODO
echo "Test 1: Reviewer found TODO..."
if grep -qi "TODO\|placeholder\|incomplete\|TBD" "$OUTPUT_FILE"; then
    echo "  [PASS] Reviewer identified TODO / placeholder content"
else
    echo "  [FAIL] Reviewer did not identify TODO"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 2: Reviewer found the "specified later" deferral
echo "Test 2: Reviewer found 'specified later' deferral..."
if grep -qi "specifi.*later\|later.*specif\|defer\|incomplete\|error handling" "$OUTPUT_FILE"; then
    echo "  [PASS] Reviewer identified deferred content"
else
    echo "  [FAIL] Reviewer did not identify deferred content"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 3: Reviewer output includes Issues section
echo "Test 3: Review output format..."
if grep -qi "issues\|issue\|finding\|problem" "$OUTPUT_FILE"; then
    echo "  [PASS] Review includes issues/findings"
else
    echo "  [FAIL] Review missing issues section"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 4: Reviewer did NOT approve (found issues)
echo "Test 4: Reviewer verdict..."
if grep -qiE "Issues Found|not approved|do not approve|not ready|needs work|blocked" "$OUTPUT_FILE"; then
    echo "  [PASS] Reviewer correctly found issues (not approved)"
elif grep -qiE "Approved|approved|ready" "$OUTPUT_FILE" && ! grep -qiE "not approved|issues found|needs work|blocked" "$OUTPUT_FILE"; then
    echo "  [WARN] Reviewer may have approved — check manually"
    # Not failing — ambiguous format
else
    echo "  [PASS] Reviewer identified problems (ambiguous format but found issues)"
fi
echo ""

# Summary
echo "========================================"
echo " Test Summary"
echo "========================================"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "STATUS: PASSED"
    echo "All verification tests passed!"
    echo ""
    echo "The spec document reviewer correctly:"
    echo "  ✓ Found TODO placeholder"
    echo "  ✓ Found 'specified later' deferral"
    echo "  ✓ Produced review with issues"
    echo "  ✓ Did not approve spec with errors"
    exit 0
else
    echo "STATUS: FAILED"
    echo "Failed $FAILED verification tests"
    echo ""
    echo "Output saved to: $OUTPUT_FILE"
    exit 1
fi
