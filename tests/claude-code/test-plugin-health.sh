#!/usr/bin/env bash
# E2E: Plugin Health Check
# Comprehensive zero-cost verification that all plugin components are intact.
# Validates: skills, hooks, scripts, workflow files, configurations.
# No Claude Code invocation needed.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "========================================"
echo " E2E: Plugin Health Check"
echo "========================================"
echo ""
echo "Plugin directory: $PLUGIN_DIR"
echo ""

# ── Section 1: All skill SKILL.md files exist and have required frontmatter ──
echo "--- Section 1: Skill Files ---"
echo ""

# Define expected skills and their key characteristics
declare -A SKILL_TITLES=(
    ["auto-mode"]="Auto Mode"
    ["finishing-a-development-branch"]="Finishing a Development Branch"
    ["image-generation"]="Image Generation"
    ["semi-auto"]="Semi-Auto"
    ["systematic-debugging"]="Systematic Debugging"
    ["using-claude-code-flow"]="Using Claude Code Flow"
    ["using-git-worktrees"]="Using Git Worktrees"
)

SKILL_COUNT=0
SKILL_ERRORS=0

for skill_name in "${!SKILL_TITLES[@]}"; do
    SKILL_FILE="$PLUGIN_DIR/skills/$skill_name/SKILL.md"
    expected_title="${SKILL_TITLES[$skill_name]}"

    if [ ! -f "$SKILL_FILE" ]; then
        fail "Skill file missing: $skill_name/SKILL.md"
        SKILL_ERRORS=$((SKILL_ERRORS + 1))
        continue
    fi

    SKILL_COUNT=$((SKILL_COUNT + 1))

    # Check frontmatter
    if head -5 "$SKILL_FILE" | grep -q "^---$"; then
        pass "$skill_name: has YAML frontmatter"
    else
        fail "$skill_name: missing YAML frontmatter"
        SKILL_ERRORS=$((SKILL_ERRORS + 1))
    fi

    # Check name field
    if grep -q "^name:" "$SKILL_FILE"; then
        pass "$skill_name: has 'name' field"
    else
        fail "$skill_name: missing 'name' field"
        SKILL_ERRORS=$((SKILL_ERRORS + 1))
    fi

    # Check description field
    if grep -q "^description:" "$SKILL_FILE"; then
        pass "$skill_name: has 'description' field"
    else
        fail "$skill_name: missing 'description' field"
        SKILL_ERRORS=$((SKILL_ERRORS + 1))
    fi
done

echo ""
echo "  Skills found: $SKILL_COUNT / ${#SKILL_TITLES[@]}"
echo ""

# ── Section 2: Hook scripts are valid Python ──
echo "--- Section 2: Hook Scripts ---"
echo ""

PYTHON_BIN="${PYTHON_BIN:-python3}"

HOOK_SCRIPTS=(
    "hooks/scripts/plan-mode-guard.py"
    "hooks/scripts/9router-intercept.py"
    "hooks/auto-mode/auto-mode-hooks.py"
    "hooks/scripts/flow-state.py"
)

for hook in "${HOOK_SCRIPTS[@]}"; do
    hook_path="$PLUGIN_DIR/$hook"
    if [ ! -f "$hook_path" ]; then
        fail "Hook script missing: $hook"
        continue
    fi

    # Verify Python syntax — use stdin to avoid path escaping issues
    if "$PYTHON_BIN" -c "import py_compile, sys; py_compile.compile(sys.argv[1], doraise=True)" "$hook_path" 2>/dev/null; then
        pass "$(basename "$hook"): valid Python syntax"
    else
        fail "$(basename "$hook"): Python syntax error"
    fi
done

echo ""

# ── Section 3: Hook configuration files ──
echo "--- Section 3: Hook Configurations ---"
echo ""

HOOK_CONFIGS=(
    "hooks/hooks.json"
    "hooks/codex-hooks.json"
)

for config in "${HOOK_CONFIGS[@]}"; do
    config_path="$PLUGIN_DIR/$config"
    if [ ! -f "$config_path" ]; then
        # codex-hooks.json may not exist — only fail for hooks.json
        if [ "$(basename "$config")" = "hooks.json" ]; then
            fail "Hook config missing: $config"
        else
            pass "$(basename "$config"): skipped (not present)"
        fi
        continue
    fi

    # Verify valid JSON — use sys.argv to avoid path escaping issues
    if "$PYTHON_BIN" -c "import json, sys; json.load(open(sys.argv[1]))" "$config_path" 2>/dev/null; then
        pass "$(basename "$config"): valid JSON"
    else
        fail "$(basename "$config"): invalid JSON"
    fi
done

echo ""

# ── Section 4: Workflow script files ──
echo "--- Section 4: Workflow Scripts ---"
echo ""

WF_SCRIPTS=(
    "skills/workflow-driven-development/execute-plan.workflow.js"
    "skills/workflow-driven-development/full-auto-pipeline.workflow.js"
)

for wf in "${WF_SCRIPTS[@]}"; do
    wf_path="$PLUGIN_DIR/$wf"
    if [ ! -f "$wf_path" ]; then
        fail "Workflow script missing: $wf"
        continue
    fi

    basename_wf=$(basename "$wf")

    # Check has meta block
    if grep -q "export const meta" "$wf_path"; then
        pass "$basename_wf: has meta export"
    else
        fail "$basename_wf: missing meta export"
    fi

    # Check braces balanced
    open=$(grep -o '{' "$wf_path" | wc -l)
    close=$(grep -o '}' "$wf_path" | wc -l)
    if [ "$open" -eq "$close" ]; then
        pass "$basename_wf: braces balanced ($open)"
    else
        fail "$basename_wf: braces unbalanced ($open vs $close)"
    fi

    # Check parentheses balanced
    open=$(grep -o '(' "$wf_path" | wc -l)
    close=$(grep -o ')' "$wf_path" | wc -l)
    if [ "$open" -eq "$close" ]; then
        pass "$basename_wf: parens balanced ($open)"
    else
        fail "$basename_wf: parens unbalanced ($open vs $close)"
    fi
done

echo ""

# ── Section 5: Prompt template files ──
echo "--- Section 5: Prompt Templates ---"
echo ""

PROMPT_TEMPLATES=(
    "skills/workflow-driven-development/implementer-prompt.md"
    "skills/workflow-driven-development/spec-reviewer-prompt.md"
    "skills/workflow-driven-development/code-quality-reviewer-prompt.md"
    "skills/workflow-driven-development/designer-prompt.md"
    "skills/workflow-driven-development/researcher-prompt.md"
    "skills/workflow-driven-development/forge-implementer-prompt.md"
    "skills/workflow-driven-development/oracle-planner-prompt.md"
    "skills/workflow-driven-development/prism-verifier-prompt.md"
    "skills/workflow-driven-development/artist-prompt.md"
)

for template in "${PROMPT_TEMPLATES[@]}"; do
    template_path="$PLUGIN_DIR/$template"
    if [ -f "$template_path" ]; then
        pass "$(basename "$template"): exists"
    else
        fail "$(basename "$template"): missing (at $template)"
    fi
done

echo ""

# ── Section 6: Script files ──
echo "--- Section 6: Support Scripts ---"
echo ""

SUPPORT_SCRIPTS=(
    "scripts/render-hooks.py"
    "scripts/statusline.sh"
)

for script in "${SUPPORT_SCRIPTS[@]}"; do
    script_path="$PLUGIN_DIR/$script"
    if [ -f "$script_path" ]; then
        pass "$(basename "$script"): exists"
    else
        fail "$(basename "$script"): missing (at $script)"
    fi
done

echo ""

# ── Section 7: Clone script validates ──
echo "--- Section 7: Clone Script ---"
echo ""

CLONE_SCRIPT="$PLUGIN_DIR/scripts/clone.sh"
if [ -f "$CLONE_SCRIPT" ]; then
    # Basic bash syntax check
    if bash -n "$CLONE_SCRIPT" 2>/dev/null; then
        pass "clone.sh: valid bash syntax"
    else
        fail "clone.sh: bash syntax error"
    fi
else
    # clone.sh might be named differently or not exist yet
    pass "clone.sh: skipped (not present)"
fi

echo ""

# ── Section 8: Skill cross-references ──
echo "--- Section 8: Skill Cross-References ---"
echo ""

# Verify each skill that references another skill actually points to an existing one
REFERENCE_CHECKS=(
    "auto-mode:finishing-a-development-branch"
    "auto-mode:using-git-worktrees"
    "auto-mode:semi-auto"
    "semi-auto:finishing-a-development-branch"
)

for ref in "${REFERENCE_CHECKS[@]}"; do
    source_skill="${ref%%:*}"
    target_skill="${ref##*:}"
    source_file="$PLUGIN_DIR/skills/$source_skill/SKILL.md"

    if [ ! -f "$source_file" ]; then
        fail "$source_skill → $target_skill: source skill not found"
        continue
    fi

    if grep -q "$target_skill" "$source_file"; then
        pass "$source_skill → $target_skill: reference exists"
    else
        fail "$source_skill → $target_skill: reference NOT found in SKILL.md"
    fi
done

echo ""

# ── Section 9: Documentation files ──
echo "--- Section 9: Documentation ---"
echo ""

DOC_FILES=(
    "README.md"
    "CLAUDE.md"
    "AGENTS.md"
    ".github/PULL_REQUEST_TEMPLATE.md"
)

for doc in "${DOC_FILES[@]}"; do
    doc_path="$PLUGIN_DIR/$doc"
    if [ -f "$doc_path" ]; then
        pass "$doc: exists"
    else
        fail "$doc: missing"
    fi
done

echo ""

# ── Summary ──
echo "========================================"
echo " Health Check Summary"
echo "========================================"
echo ""

report_failures
