# Claude Code Skills Tests

Automated tests for claude-code-flow skills using Claude Code CLI.

## Overview

This test suite verifies that skills are loaded correctly and Claude follows them as expected. Tests invoke Claude Code in headless mode (`claude -p`) and verify the behavior.

## Requirements

- Claude Code CLI installed and in PATH (`claude --version` should work)
- Local claude-code-flow plugin installed (see main README for installation)

## Running Tests

### Run all fast tests (recommended):
```bash
./run-skill-tests.sh
```

### Run integration tests (slow, 10-30 minutes):
```bash
./run-skill-tests.sh --integration
```

### Run specific test:
```bash
./run-skill-tests.sh --test test-auto-mode dynamic workflow.sh
```

### Run with verbose output:
```bash
./run-skill-tests.sh --verbose
```

### Set custom timeout:
```bash
./run-skill-tests.sh --timeout 1800  # 30 minutes for integration tests
```

## Test Structure

### test-helpers.sh
Common functions for skills testing:
- `run_claude "prompt" [timeout]` - Run Claude with prompt
- `assert_contains output pattern name` - Verify pattern exists
- `assert_not_contains output pattern name` - Verify pattern absent
- `assert_count output pattern count name` - Verify exact count
- `assert_order output pattern_a pattern_b name` - Verify order
- `create_test_project` - Create temp test directory
- `create_test_plan project_dir` - Create sample plan file

### Test Files

Each test file:
1. Sources `test-helpers.sh`
2. Runs Claude Code with specific prompts
3. Verifies expected behavior using assertions
4. Returns 0 on success, non-zero on failure

## Example Test

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/test-helpers.sh"

echo "=== Test: My Skill ==="

# Ask Claude about the skill
output=$(run_claude "What does the my-skill skill do?" 30)

# Verify response
assert_contains "$output" "expected behavior" "Skill describes behavior"

echo "=== All tests passed ==="
```

## Current Tests

### Static Tests (zero-cost, run first)

These tests are instant — no Claude Code invocation needed.

#### test-plugin-health.sh
Comprehensive plugin health check:
- All 16 skill SKILL.md files exist with valid YAML frontmatter (name + description)
- All 4 hook scripts have valid Python syntax
- Hook configuration files (hooks.json) are valid JSON
- Workflow scripts (full-auto-pipeline) have balanced brackets + meta blocks
- Prompt template files (implementer, spec-reviewer, code-reviewer, designer, researcher, forge, oracle, prism, artist) all exist
- Support scripts (render-hooks.py, statusline.sh) exist
- Cross-skill references resolve to existing SKILL.md files
- Documentation files (README.md, CLAUDE.md, AGENTS.md, PR template) exist

#### test-pipeline-chain.sh
Simplified pipeline chain integrity verification:
- User-facing skill surface is compact
- Deleted skills are not exposed
- Auto-mode owns full workflow
- auto-mode owns guided planning
- Internal workflow engine files exist
- Cross-skill reference consistency (no broken links)

#### test-auto-mode-workflow-structure.sh
Workflow script static checks:
- File existence and workflow-engine.md title
- JS structure: balanced braces/parens/brackets, meta block, required fields
- Schema definitions: IMPLEMENT_RESULT + REVIEW_RESULT with correct enum values
- Behavioral content embedded in workflow scripts
- Canonical prompt files exist, WF duplicates correctly removed
- Pipeline/parallel/retry/blocked handling in script logic

#### test-designer-prompt-content.sh
Designer prompt content verification:
- Source provenance in synthesize step
- Format reference source requirements
- DESIGN.md traceability
- Web tools present (WebSearch, WebFetch)
- Phase 1 structure preserved
- Format reference wired correctly

#### test-researcher-prompt-content.sh
Researcher prompt content verification:
- Local tools section (Glob, Grep, CodeGraph)
- Web tools section (WebSearch, WebFetch)
- Source provenance tags (source: local/web/both)
- Cross-verification step
- Conflict resolution with confidence downgrade
- Cross-reference table
- Dual-source quality checklist
- 6-step research method

### Behavioral Tests (use claude -p, ~2 min each)

Each test verifies skill behavior through Claude Code CLI prompts.

#### test-git-worktrees-e2e.sh
Git worktrees skill:
- Skill name and isolation/workspace purpose
- Worktree creation process (EnterWorktree tool)
- Clean baseline verification requirement
- Main/master branch protection
- Finishing skill integration

#### test-finishing-e2e.sh
Finishing a development branch:
- Skill name and merge/PR/cleanup purpose
- Four completion options
- Pre-finish verification requirement
- Worktree cleanup after finishing

#### test-debugging-e2e.sh
Systematic debugging:
- Skill name and structured process
- Root cause vs symptoms focus
- Hypothesis-driven approach
- Post-fix verification and regression checks

#### test-worktree-native-preference.sh
Tool preference verification:
- Agent uses EnterWorktree (not raw git worktree add)
- Configurable run count for statistical significance

### Integration Tests (use --integration flag)

#### test-hook-interception.sh
Hook interception test:
- plan-mode-guard blocks EnterPlanMode
- 9router-intercept handles WebSearch
- 9router-intercept handles WebFetch

#### test-auto-mode-hooks.sh
Auto-mode hook lifecycle (Python-based):
- Stop hook blocks active tasks
- SubagentStart injects context
- SubagentStop handles empty/gave-up/untracked/reviewer output
- PreCompact writes snapshot
- - TeammateIdle with/without team
- Corrupt state.json handling
- Multiple active task selection
- hooks.json structure validation

#### test-document-review-system.sh
Document review system:
- Provides spec with intentional errors (TODO, deferred content)
- Verifies reviewer catches all errors
- Verifies reviewer does not approve flawed spec

#### test-research-pipeline.sh
Research pipeline E2E (long-running, 5-10 min):
- Brainstorming triggers on naive prompt
- Research output directory verification
- Writing-plans dispatches researcher
- Source provenance in research files

## Adding New Tests

1. Create new test file: `test-<skill-name>.sh`
2. Source test-helpers.sh
3. Write tests using `run_claude` and assertions
4. Add to test list in `run-skill-tests.sh`
5. Make executable: `chmod +x test-<skill-name>.sh`

## Timeout Considerations

- Default timeout: 5 minutes per test
- Claude Code may take time to respond
- Adjust with `--timeout` if needed
- Tests should be focused to avoid long runs

## Debugging Failed Tests

With `--verbose`, you'll see full Claude output:
```bash
./run-skill-tests.sh --verbose --test test-auto-mode dynamic workflow.sh
```

Without verbose, only failures show output.

## CI/CD Integration

To run in CI:
```bash
# Run with explicit timeout for CI environments
./run-skill-tests.sh --timeout 900

# Exit code 0 = success, non-zero = failure
```

## Notes

- Tests verify skill *instructions*, not full execution
- Full workflow tests would be very slow
- Focus on verifying key skill requirements
- Tests should be deterministic
- Avoid testing implementation details


