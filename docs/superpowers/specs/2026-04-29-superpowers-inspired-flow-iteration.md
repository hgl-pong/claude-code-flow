# Superpowers-Inspired Flow Iteration

## Goal

Strengthen `claude-code-flow` by adopting the most useful workflow ideas from `obra/superpowers` while keeping this plugin's model-tiered agent architecture.

## Reference

Source reviewed: `https://github.com/obra/superpowers`, commit `6efe32c9e2dd002d0c394e861e0529675d1ab32e`.

Relevant ideas:

- Skills are mandatory workflow tools, not optional reference docs.
- Broad development starts with design and approval.
- Implementation plans should be concrete enough for fresh agents.
- Behavior changes use test-first development.
- Review is staged: spec compliance before code quality.
- Completion requires fresh verification evidence.

## Changes

### New Skills

- `using-claude-code-flow`: entry-point skill selection and workflow discipline.
- `brainstorming`: design and approval gate before creative implementation.
- `writing-plans`: concrete, test-first task plans.
- `systematic-debugging`: evidence-first root cause workflow.
- `verification-before-completion`: final evidence checklist.

### Updated Skills

- `dev-orchestrator`: now explicitly coordinates skill check, brainstorming, plan writing, TDD, debugging, staged review, acceptance, and verification.
- `testing-strategy`: now treats TDD as the default for production behavior changes and defines evidence expectations.

### New Commands

- `/brainstorm`: refine an idea into an approved design.
- `/write-plan`: write a test-first implementation plan.
- `/execute-plan`: execute an approved plan through implementation, review, acceptance, and verification.

### Updated Commands

- `/workflow-plan`: starts with skill selection and brainstorming when needed, then creates an execution plan.
- `/quick-fix`: adds systematic debugging for unknown root cause and test-first behavior changes.
- `/write-tests`: routes through testing strategy and emphasizes behavior tests.

### Updated Agents

- Implementation agents (`forge`, `weaver`) now require enough context before editing, use test-first behavior changes, and report RED/GREEN/build evidence.
- Test/build agents (`prism`, `anvil`) now require failing-test or reproduced-build evidence before fixes and exact verification results after changes.
- Planning/design agents (`oracle`, `atlas`, `designer`) now make design gates, test strategy, states, breakpoints, and implementable handoffs explicit.
- Research/review/acceptance agents (`scout`, `sentinel`, `validator`) now produce planning impact, require spec compliance before quality review, and verify evidence freshness.
- Documentation/evolution agents (`chronicler`, `evolver`) now avoid unverified claims and require data-backed, validated prompt improvement proposals.

### Updated Hooks

- Added `PostToolUse(Bash)` verification tracking via `hooks/scripts/track-verification.py`.
- Verification evidence is written to `.claude/flow/verification-evidence.jsonl` and `.claude/flow/last-verification.json`.
- `workflow-state.json` records `verification_count` and `last_verification`.
- Pre-compact context, workflow status, metrics, workflow stop summaries, and statusline now surface latest verification evidence.

### Tests

- Added `tests/test_plugin_integrity.py` and `tests/run-tests.py`.
- Tests cover plugin JSON, markdown frontmatter, hook references, Python hook syntax, shell LF endings, verification evidence tracking, flow-state default merging, and metrics aggregation.
- Added optional Claude Code E2E tests under `tests/claude-code/` that invoke `claude -p` to verify workflow skill explanations, command ordering, and running local regression tests through Claude.

## Non-Goals

- No direct copy of Superpowers skill prose.
- No new runtime dependencies.
- No change to existing agent names or hook scripts.

## Verification

- Validate plugin metadata JSON.
- Confirm all command and skill files are discoverable.
- Check frontmatter names/descriptions exist for new files.
