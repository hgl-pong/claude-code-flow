#!/usr/bin/env bash
# E2E: Simplified pipeline chain verification
# Verifies the compact skill surface:
# auto-mode / semi-auto → workflow scripts → finishing
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Simplified Pipeline Chain"
echo "========================================"
echo ""

# ── Test 1: User-facing skill surface ──
echo "--- Test 1: Skill surface ---"
echo ""

EXPECTED_SKILLS=(
  "auto-mode"
  "semi-auto"
  "systematic-debugging"
  "using-claude-code-flow"
  "using-git-worktrees"
  "finishing-a-development-branch"
  "image-generation"
)

for skill in "${EXPECTED_SKILLS[@]}"; do
  if [ -f "$PLUGIN_DIR/skills/$skill/SKILL.md" ]; then
    pass "Skill exists: $skill"
  else
    fail "Skill missing: $skill"
  fi
done

REMOVED_SKILLS=(
  "brainstorming"
  "dispatching-parallel-agents"
  "test-driven-development"
  "requesting-code-review"
  "receiving-code-review"
  "writing-skills"
  "writing-plans"
  "executing-plans"
  "verification-before-completion"
  "workflow-driven-development"
)

for skill in "${REMOVED_SKILLS[@]}"; do
  if [ -f "$PLUGIN_DIR/skills/$skill/SKILL.md" ]; then
    fail "Deleted skill still exposed: $skill"
  else
    pass "Deleted skill not exposed: $skill"
  fi
done

echo ""

# ── Test 2: Auto-mode owns full workflow ──
echo "--- Test 2: Auto-mode integration ---"
echo ""

AUTO_FILE="$PLUGIN_DIR/skills/auto-mode/SKILL.md"
for text in "full-auto-pipeline.workflow.js" "multi-agent brainstorming" "completion gates" "finishing-a-development-branch" "semi-auto"; do
  if grep -qi "$text" "$AUTO_FILE"; then
    pass "Auto-mode includes: $text"
  else
    fail "Auto-mode missing: $text"
  fi
done

echo ""

# ── Test 3: Semi-auto owns guided planning ──
echo "--- Test 3: Semi-auto integration ---"
echo ""

SEMI_FILE="$PLUGIN_DIR/skills/semi-auto/SKILL.md"
for text in "Clarify" "Research" "approved spec" "executable plan" "execute-plan.workflow.js" "finishing-a-development-branch"; do
  if grep -qi "$text" "$SEMI_FILE"; then
    pass "Semi-auto includes: $text"
  else
    fail "Semi-auto missing: $text"
  fi
done

echo ""

# ── Test 4: Internal workflow engine files ──
echo "--- Test 4: Workflow engine files ---"
echo ""

for path in \
  "skills/workflow-driven-development/execute-plan.workflow.js" \
  "skills/workflow-driven-development/full-auto-pipeline.workflow.js" \
  "skills/workflow-driven-development/workflow-engine.md" \
  "skills/workflow-driven-development/implementer-prompt.md" \
  "skills/workflow-driven-development/spec-reviewer-prompt.md" \
  "skills/workflow-driven-development/code-quality-reviewer-prompt.md"; do
  if [ -f "$PLUGIN_DIR/$path" ]; then
    pass "Workflow engine file exists: $path"
  else
    fail "Workflow engine file missing: $path"
  fi
done

echo ""

# ── Test 5: Cross-skill references resolve ──
echo "--- Test 5: Cross-skill references ---"
echo ""

REF_REGEX='claude-code-flow:[a-z-]+'
VIOLATIONS=0
for skill_file in "$PLUGIN_DIR"/skills/*/SKILL.md; do
  [ -f "$skill_file" ] || continue
  skill="$(basename "$(dirname "$skill_file")")"
  refs=$(grep -oE "$REF_REGEX" "$skill_file" 2>/dev/null | sort -u || true)
  for ref in $refs; do
    ref_skill="${ref#claude-code-flow:}"
    [ "$ref_skill" = "$skill" ] && continue
    ref_file="$PLUGIN_DIR/skills/$ref_skill/SKILL.md"
    if [ ! -f "$ref_file" ]; then
      fail "Broken ref: $skill → $ref_skill"
      VIOLATIONS=$((VIOLATIONS + 1))
    fi
  done
done

if [ "$VIOLATIONS" -eq 0 ]; then
  pass "All cross-skill references resolve"
fi

echo ""
echo "========================================"
echo " Pipeline Chain Summary"
echo "========================================"
echo ""

report_failures
