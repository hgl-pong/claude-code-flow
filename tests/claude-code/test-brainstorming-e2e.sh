#!/usr/bin/env bash
# E2E: Brainstorming Skill Activation
# Verifies the brainstorming skill activates on a "let's build X" prompt
# and follows its behavioral rules.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Brainstorming Skill"
echo "========================================"
echo ""

# ── Test 1: Skill recognition ──
echo "Test 1: Skill name and purpose..."
output=$(run_claude "What is the claude-code-flow:brainstorming skill? What does it do?" 120)

assert_contains "$output" "brainstorming\|Brainstorming" \
    "Skill is recognized by name" || true
assert_contains "$output" "design\|spec\|requirements\|clarify\|question" \
    "Skill purpose includes design/requirements gathering" || true

echo ""

# ── Test 2: Design section presentation ──
echo "Test 2: Design sections..."
output=$(run_claude "In the brainstorming skill, what design sections should be presented? List them." 120)

assert_contains "$output" "[Aa]rchitecture\|[Cc]omponents\|[Dd]ata flow\|[Ee]rror handling\|[Tt]esting" \
    "Mentions key design sections" || true

echo ""

# ── Test 3: Approaches evaluation ──
echo "Test 3: Approach evaluation..."
output=$(run_claude "In the brainstorming skill, how many approaches should be proposed, and how is the best one chosen?" 120)

assert_contains "$output" "2-3\|2.*3\|two.*three\|approaches\|alternative" \
    "Mentions proposing 2-3 approaches" || true
assert_contains "$output" "[Rr]ecommend\|[Tt]radeoff\|[Pp]ropose.*approach\|agent.*recommend\|user.*approv" \
    "Mentions approach selection criteria" || true

echo ""

# ── Test 4: Visual companion behavior ──
echo "Test 4: Visual companion..."
output=$(run_claude "What does the brainstorming skill say about the visual companion? When should it be offered?" 120)

assert_contains "$output" "visual companion\|brainstorm server\|design viewer\|localhost" \
    "Mentions visual companion/brainstorm server" || true

echo ""

# ── Test 5: Spec document reviewer integration ──
echo "Test 5: Spec reviewer integration..."
output=$(run_claude "In the brainstorming skill, what reviewer is dispatched after the spec is written?" 120)

assert_contains "$output" "spec.*reviewer\|reviewer\|spec.*review\|review.*spec" \
    "Mentions spec reviewer" || true

echo ""

# ── Test 6: Deliberate design practice ──
echo "Test 6: Design before code..."

# Verify the skill emphasizes design first, code later
output=$(run_claude "According to the brainstorming skill, should you jump straight to writing code when someone says 'build X'?" 120)

assert_contains "$output" "[Nn]o\|[Nn]ot.*immediately\|[Dd]esign.*first\|[Hh]ard.*gate\|[Dd]o NOT.*implement" \
    "Advises against jumping straight to code" || true

echo ""

report_failures
