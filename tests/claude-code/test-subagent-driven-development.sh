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

assert_contains "$output" "subagent-driven-development\|Subagent-driven-development\|Subagent-Driven Development\|Subagent Driven" "Skill is recognized" || true
assert_contains "$output" "Load Plan\|[Rr]ead.*plan\|extract.*tasks\|extract.*task" "Mentions loading plan" || true

echo ""

# Test 2: Verify skill describes correct workflow order
echo "Test 2: Workflow ordering..."

output=$(run_claude "In the subagent-driven-development skill, what comes first: spec compliance review or code quality review? Be specific about the order." )

assert_contains "$output" "[Ss]pec.*comes first\|[Ss]pec.*first.*code\|[Ss]pec.*before.*code\|[Ss]pec compliance.*before\|[Ss]pec.*Stage 1" "Spec compliance before code quality" || true

echo ""

# Test 3: Verify self-review is mentioned
echo "Test 3: Self-review requirement..."

output=$(run_claude "Does the subagent-driven-development skill require implementers to do self-review? What should they check?" )

assert_contains "$output" "self-review\|self review" "Mentions self-review" || true
assert_contains "$output" "completeness\|Completeness\|Spec match\|Spec fit\|all reqs\|reqs met\|reqs all met\|omissions\|[Ss]pec met\|[Ss]pec reqs all met\|[Ss]pec complete\|[Ss]pec fully met\|task spec fully met\|missed reqs\|missing reqs\|[Mm]issing functionality\|[Mm]issing flags\|[Aa]ll tests pass\|bugs\|oversights\|match.*task spec" "Checks completeness" || true

echo ""

# Test 4: Verify plan is read once
echo "Test 4: Plan reading efficiency..."

output=$(run_claude "In subagent-driven-development, how many times should the controller read the plan file? When does this happen?" )

assert_contains "$output" "once\|Once\|one time\|single" "Read plan once" || true
assert_contains "$output" "Step 1\|beginning\|start\|Load Plan\|一次\|开始时\|流程.*开始\|before.*task" "Read at beginning" || true

echo ""

# Test 5: Verify spec compliance reviewer is skeptical
echo "Test 5: Spec compliance reviewer mindset..."

output=$(run_claude "What is the spec compliance reviewer's attitude toward the implementer's report in subagent-driven-development?" )

assert_contains "$output" "not trust\|do not trust\|don't trust\|[Ss]keptical\|[Uu]ntrusted\|[Ss]uspicious\|verify.*independently\|independently.*read" "Reviewer is skeptical" || true
assert_contains "$output" "[Rr]ead.*code\|inspect.*code\|verify.*code\|trust code\|verify independently\|actual code" "Reviewer reads code" || true

echo ""

# Test 6: Verify review loops
echo "Test 6: Review loop requirements..."

output=$(run_claude "In subagent-driven-development, what happens if a reviewer finds issues? Is it a one-time review or a loop?" )

assert_contains "$output" "loop\|again\|repeat\|until.*approved\|until.*compliant" "Review loops mentioned" || true
assert_contains "$output" "implementer.*fix\|fix.*issues" "Implementer fixes issues" || true

echo ""

# Test 7: Verify full task text is provided
echo "Test 7: Task context provision..."

output=$(run_claude "In subagent-driven-development, how does the controller provide task information to the implementer subagent? Does it make them read a file or provide it directly?" )

assert_contains "$output" "provide.*directly\|full.*text\|paste\|include.*prompt" "Provides text directly" || true
assert_contains "$output" "never.*read\|[Nn]ot.*read.*file\|[Nn]ot file-read\|don't.*read.*file\|don't.*read.*file\|does not.*read\|should not.*read\|provide full text" "Doesn't make subagent read file" || true

echo ""

# Test 8: Verify worktree requirement
echo "Test 8: Worktree requirement..."

output=$(run_claude "What workflow skills are required before using subagent-driven-development? List any prerequisites or required skills." )

assert_contains "$output" "using-git-worktrees\|worktree" "Mentions worktree requirement" || true

echo ""

# Test 9: Verify main branch warning
echo "Test 9: Main branch red flag..."

output=$(run_claude "In subagent-driven-development, is it okay to start implementation directly on the main branch?" )

assert_contains "$output" "worktree\|feature.*branch\|not.*main\|never.*main\|avoid.*main\|don't.*main\|consent\|permission" "Warns against main branch" || true

echo ""

# Test 10: Verify researcher, designer, and design reviewer templates
echo "Test 10: Researcher, designer, and design reviewer templates..."

output=$(run_claude "What specialized subagent templates does subagent-driven-development have for research, UI design work, and reviewing DESIGN.md?" )

assert_contains "$output" "researcher" "Mentions researcher template" || true
assert_contains "$output" "designer" "Mentions designer template" || true
assert_contains "$output" "design-reviewer\|design reviewer" "Mentions design reviewer template" || true

echo ""

# Test 11: Verify UI implementation consumes approved DESIGN.md
echo "Test 11: UI implementation consumes DESIGN.md..."

output=$(run_claude "In subagent-driven-development's UI Implementation Constraint, what must the controller read/include before dispatching an implementer for a visible UI task when DESIGN.md exists?" )

assert_contains "$output" "DESIGN\.md\|DESIGN" "Mentions DESIGN.md" || true
assert_contains "$output" "approved\|read\|consume\|binding\|tokens\|component states\|constraint" "Mentions approved design constraints" || true

echo ""

# ===== Parallel Execution Tests =====

# Test 12: Parallel execution section exists
echo "Test 12: Parallel execution support..."
output=$(run_claude "Does the subagent-driven-development skill support running multiple tasks in parallel? How does it decide which tasks can run concurrently?" )
assert_contains "$output" "CCF_MAX_PARALLEL_AGENTS\|pool\|parallel\|concurrent" "Parallel execution documented" || true
assert_contains "$output" "depends_on\|dependency.*graph\|dependenc" "Dependency graph documented" || true
echo ""

# Test 13: CCF_MAX_PARALLEL_AGENTS env var
echo "Test 13: CCF_MAX_PARALLEL_AGENTS environment variable..."
output=$(run_claude "What is the purpose of CCF_MAX_PARALLEL_AGENTS in subagent-driven-development? What is the default value?" )
assert_contains "$output" "CCF_MAX_PARALLEL_AGENTS\|max.*parallel.*agent" "Env var mentioned" || true
assert_contains "$output" "5\|five\|default.*5" "Default value 5" || true
echo ""

# Test 14: Event-driven dispatch — review fires immediately
echo "Test 14: Event-driven dispatch — review fires on completion..."
output=$(run_claude "In the parallel execution model of subagent-driven-development, what happens immediately when an implementer subagent finishes? Does other work continue while reviews run?" )
assert_contains "$output" "immediately\|right away\|as soon as\|fire.*next" "Review fires immediately" || true
assert_contains "$output" "overlap\|while.*still.*run\|other.*continue\|parallel\|concurrent" "Review overlaps with implementation" || true
echo ""

# Test 15: Pool slot filling
echo "Test 15: Pool slot filling on completion..."
output=$(run_claude "When a subagent completes and its review chain finishes, what does the pool do with the vacant slot?" )
assert_contains "$output" "fill.*slot\|fill.*pool\|dispatch.*next\|refill\|vacant\|available.*slot" "Vacant slots are filled" || true
echo ""

# Test 16: Shared-file parallel safety
echo "Test 16: Shared-file parallel safety red flag..."
output=$(run_claude "According to subagent-driven-development, is it allowed to dispatch tasks that share files or dependencies in parallel?" )
assert_contains "$output" "not.*dispatch\|don't.*dispatch\|never.*dispatch\|should not.*dispatch\|not.*parallel\|avoid.*parallel" "Tasks sharing files NOT dispatched in parallel" || true
echo ""

# Test 17: Dependency-gated dispatch
echo "Test 17: Dependency-gated dispatch..."
output=$(run_claude "Can subagent-driven-development dispatch a task whose depends_on tasks are not yet done?" )
assert_contains "$output" "not.*dispatch\|don't.*dispatch\|cannot\|should not\|never\|not.*until\|wait" "Tasks with unmet deps not dispatched" || true
echo ""

# Test 18: Always rules — dependency graph + fill pool
echo "Test 18: Always rules for parallel execution..."
output=$(run_claude "What does subagent-driven-development say you must ALWAYS do regarding the dependency graph and pool capacity?" )
assert_contains "$output" "build.*dependency.*graph\|respect.*dependency\|fill.*pool\|fill.*capacity" "Always rules exist" || true
echo ""

# Test 19: Old sequential-only red flag is gone
echo "Test 19: Old sequential-only constraint removed..."
output=$(run_claude "Does subagent-driven-development still forbid dispatching multiple implementation subagents in parallel? Is there a 'Never' rule that says dispatch multiple implementation subagents in parallel conflicts?" )
assert_not_contains "$output" "Never.*Dispatch multiple implementation subagents in parallel" "Old parallel ban removed" || true
echo ""

report_failures
exit $?
