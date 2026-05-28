#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

cd "$TMPDIR"

git init
git config user.email "test@test"
git config user.name "Test"

mkdir -p .claude/skills/auto-mode
cp "$REPO_ROOT/skills/auto-mode/SKILL.md" .claude/skills/auto-mode/SKILL.md

mkdir -p .claude/skills/using-claude-code-flow
cat > .claude/skills/using-claude-code-flow/SKILL.md << 'BOOTSTRAP'
---
name: using-claude-code-flow
description: Bootstrap
---
BOOTSTRAP

git add . && git commit -m "scaffold"

echo ""
echo "=== Test 1: /auto triggers auto-mode skill ==="
echo ""

ACTUAL_OUTPUT="$TMPDIR/test1-result.txt"

claude --print --output-format stream-json -p "/auto build a react todo list" 2>&1 | tee "$ACTUAL_OUTPUT" || true

if grep -q '"name":"Skill".*"auto-mode"' "$ACTUAL_OUTPUT"; then
    echo "PASS: /auto triggers Skill(auto-mode)"
else
    echo "FAIL: /auto did NOT trigger Skill(auto-mode)"
    exit 1
fi

echo ""
echo "=== Test 2: 全自动模式 triggers auto-mode skill ==="
echo ""

ACTUAL_OUTPUT2="$TMPDIR/test2-result.txt"

claude --print --output-format stream-json -p "全自动模式 帮我做一个react todo list" 2>&1 | tee "$ACTUAL_OUTPUT2" || true

if grep -q '"name":"Skill".*"auto-mode"' "$ACTUAL_OUTPUT2"; then
    echo "PASS: 全自动模式 triggers Skill(auto-mode)"
else
    echo "FAIL: 全自动模式 did NOT trigger Skill(auto-mode)"
    exit 1
fi

cd "$REPO_ROOT"
echo ""
echo "All auto-mode trigger tests passed."
