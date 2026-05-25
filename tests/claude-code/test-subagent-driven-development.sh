#!/usr/bin/env bash
# Test: subagent-driven-development skill
# Verifies that the skill is loaded and follows correct workflow
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: subagent-driven-development skill ==="
echo ""

# Test 1: Verify skill can be loaded
echo "Test 1: Skill loading..."

output=$(run_claude "What is the subagent-driven-development skill? Describe its key steps briefly." )

if assert_contains "$output" "subagent-driven-development\|Subagent-Driven Development\|Subagent Driven" "Skill is recognized"; then
    : # pass
else
    exit 1
fi

if assert_contains "$output" "Load Plan\|[Rr]ead.*plan\|extract.*tasks\|extract.*task" "Mentions loading plan"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 2: Verify skill describes correct workflow order
echo "Test 2: Workflow ordering..."

output=$(run_claude "In the subagent-driven-development skill, what comes first: spec compliance review or code quality review? Be specific about the order." )

if assert_contains "$output" "[Ss]pec.*comes first\|[Ss]pec.*first.*code\|[Ss]pec.*before.*code\|[Ss]pec compliance.*before\|[Ss]pec.*Stage 1" "Spec compliance before code quality"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 3: Verify self-review is mentioned
echo "Test 3: Self-review requirement..."

output=$(run_claude "Does the subagent-driven-development skill require implementers to do self-review? What should they check?" )

if assert_contains "$output" "self-review\|self review" "Mentions self-review"; then
    : # pass
else
    exit 1
fi

if assert_contains "$output" "completeness\|Completeness\|Spec match\|Spec fit\|all reqs\|reqs met\|reqs all met\|omissions\|[Ss]pec met\|[Ss]pec reqs all met\|[Ss]pec complete\|[Ss]pec fully met\|task spec fully met\|missed reqs\|missing reqs" "Checks completeness"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 4: Verify plan is read once
echo "Test 4: Plan reading efficiency..."

output=$(run_claude "In subagent-driven-development, how many times should the controller read the plan file? When does this happen?" )

if assert_contains "$output" "once\|Once\|one time\|single" "Read plan once"; then
    : # pass
else
    exit 1
fi

if assert_contains "$output" "Step 1\|beginning\|start\|Load Plan\|一次\|开始时\|流程.*开始\|before.*task" "Read at beginning"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 5: Verify spec compliance reviewer is skeptical
echo "Test 5: Spec compliance reviewer mindset..."

output=$(run_claude "What is the spec compliance reviewer's attitude toward the implementer's report in subagent-driven-development?" )

if assert_contains "$output" "not trust\|do not trust\|don't trust\|skeptical\|[Ss]uspicious\|verify.*independently\|independently.*read" "Reviewer is skeptical"; then
    : # pass
else
    exit 1
fi

if assert_contains "$output" "[Rr]ead.*code\|inspect.*code\|verify.*code\|trust code\|verify independently\|actual code" "Reviewer reads code"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 6: Verify review loops
echo "Test 6: Review loop requirements..."

output=$(run_claude "In subagent-driven-development, what happens if a reviewer finds issues? Is it a one-time review or a loop?" )

if assert_contains "$output" "loop\|again\|repeat\|until.*approved\|until.*compliant" "Review loops mentioned"; then
    : # pass
else
    exit 1
fi

if assert_contains "$output" "implementer.*fix\|fix.*issues" "Implementer fixes issues"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 7: Verify full task text is provided
echo "Test 7: Task context provision..."

output=$(run_claude "In subagent-driven-development, how does the controller provide task information to the implementer subagent? Does it make them read a file or provide it directly?" )

if assert_contains "$output" "provide.*directly\|full.*text\|paste\|include.*prompt" "Provides text directly"; then
    : # pass
else
    exit 1
fi

if assert_contains "$output" "never.*read\|[Nn]ot.*read.*file\|[Nn]ot file-read\|don't.*read.*file\|don’t.*read.*file\|does not.*read\|should not.*read\|provide full text" "Doesn't make subagent read file"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 8: Verify worktree requirement
echo "Test 8: Worktree requirement..."

output=$(run_claude "What workflow skills are required before using subagent-driven-development? List any prerequisites or required skills." )

if assert_contains "$output" "using-git-worktrees\|worktree" "Mentions worktree requirement"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 9: Verify main branch warning
echo "Test 9: Main branch red flag..."

output=$(run_claude "In subagent-driven-development, is it okay to start implementation directly on the main branch?" )

if assert_contains "$output" "worktree\|feature.*branch\|not.*main\|never.*main\|avoid.*main\|don't.*main\|consent\|permission" "Warns against main branch"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 10: Verify researcher, designer, and design reviewer templates
echo "Test 10: Researcher, designer, and design reviewer templates..."

output=$(run_claude "What specialized subagent templates does subagent-driven-development have for research, UI design work, and reviewing DESIGN.md?" )

if assert_contains "$output" "researcher" "Mentions researcher template"; then
    : # pass
else
    exit 1
fi

if assert_contains "$output" "designer" "Mentions designer template"; then
    : # pass
else
    exit 1
fi

if assert_contains "$output" "design-reviewer\|design reviewer" "Mentions design reviewer template"; then
    : # pass
else
    exit 1
fi

echo ""

# Test 11: Verify UI implementation consumes approved DESIGN.md
echo "Test 11: UI implementation consumes DESIGN.md..."

output=$(run_claude "In subagent-driven-development's UI Implementation Constraint, what must the controller read/include before dispatching an implementer for a visible UI task when DESIGN.md exists?" )

if assert_contains "$output" "DESIGN\.md\|DESIGN" "Mentions DESIGN.md"; then
    : # pass
else
    exit 1
fi

if assert_contains "$output" "approved\|read\|consume\|binding\|tokens\|component states\|constraint" "Mentions approved design constraints"; then
    : # pass
else
    exit 1
fi

echo ""

echo "=== All subagent-driven-development skill tests passed ==="
