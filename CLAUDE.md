# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Code Flow is a **Claude Code plugin** (not a standalone application) that orchestrates multi-step development workflows through a pipeline of specialized AI agents. It has no build system, no package manager, and no compilation step — the entire project is markdown prompts, Python hook scripts, and shell scripts.

## Testing

```bash
# Fast local regression tests (no CLI/network dependencies)
python tests/run-tests.py

# Run a single test file
python -m unittest tests.test_plugin_integrity

# E2E tests via Claude Code headless (optional, costs tokens)
bash tests/claude-code/run-e2e-tests.sh
bash tests/claude-code/run-e2e-tests.sh --test test-skill-brainstorming.sh

# Integration tests (10-30 min, real token cost)
bash tests/claude-code/run-e2e-tests.sh --integration

# Skill auto-loading verification
bash tests/skill-triggering/run-all.sh
```

## Architecture

### Source of Truth

Keep workflow details in one place:

| Topic | Authoritative file |
|---|---|
| Agent roles, models, and behavioral constraints | `agents/*.md` |
| Entry routing, trigger bias, and mode selection | `skills/dev-orchestrator/SKILL.md` |
| Gate checklist, ordering, scheduling, review, and acceptance | `skills/dev-orchestrator/references/pipeline-operations.md` |
| Review command boundaries, sentinel inputs, and fix loops | `skills/dev-orchestrator/references/review.md` |
| Diagnostic runtime files, metrics commands, and output rules | `skills/dev-orchestrator/references/diagnostics.md` |
| Parallel dispatch, decomposition, inter-agent handoff | `skills/dev-orchestrator/references/parallel-dispatch.md` |
| Verification gate and evidence standards | `skills/dev-orchestrator/references/verification-gate.md` |
| Branch completion (merge, PR, keep, discard) | `skills/dev-orchestrator/references/finish-branch.md` |
| Subagent prompt templates | `skills/dev-orchestrator/references/subagent-prompts.md` |
| Plan writing and execution | `skills/planning/SKILL.md` |
| Code review (performing + receiving) | `skills/code-review/SKILL.md` |
| Slash command entry points | `commands/*.md` as thin routers |
| Runtime workflow state | `.claude/flow/plan-state.json` and `.claude/flow/workflow-state.json` |
| Hook registration and scripts | `scripts/render-hooks.py` renders `hooks/hooks.json` and `hooks/codex-hooks.json`; scripts live in `hooks/scripts/*` |

Top-level docs should summarize and link to these files rather than duplicating long gate checklists.

### Workflow Pipeline

Agent definitions live in `agents/*.md`; the pipeline contract lives in
`skills/dev-orchestrator/references/pipeline-operations.md`. This file only
names the routing rules Claude Code needs at session start.

Research is handled by the `research` skill, dispatched as general-purpose
subagents with inlined methodology. No dedicated research agent exists. **Never
use `subagent_type: "claude-code-flow:research"`; always use
`subagent_type: "general-purpose"`.**

When work references another repo, plugin, agent pack, or external workflow,
run `workflow-intake` before oracle planning. It records Adopt / Adapt / Reject /
Defer decisions without importing a competing workflow surface.

`/plan` is the plugin planning entry; `EnterPlanMode` is guarded so model-triggered
built-in plan mode redirects back to the plugin workflow. Host-level plan transitions
such as Shift+Tab or SDK permission-mode changes cannot be fully intercepted by a plugin.

`dev-orchestrator` is the **default entry skill** — it handles entry routing for
unclassified tasks and owns the execution pipeline. It absorbs verification,
branch finishing, and parallel dispatch as reference phases. Specialized skills
(`brainstorming`, `planning`, `code-review`, `research`, `design`,
`engineering-ops`, `testing-strategy`, `systematic-debugging`) handle concerns
outside the main pipeline.

### Autonomous Mode

- **ULI (Ultra Loop Iteration)**: Product iteration loop with PD agent proposing requirements each cycle. Legacy `ulw`/`ultrawork` prompts route into ULI. Stop hook blocks until `<uli-done>`.

### Hook System

Hook manifests are generated snapshots from `scripts/render-hooks.py`; scripts
live in `hooks/scripts/`. Do not hand-maintain duplicated Claude/Codex hook
tables in documentation.

### State Machine

Runtime state lives in `.claude/flow/` (gitignored). Key files:
- `workflow-state.json`: Current phase (idle/plan/design/impl/review), mode, tasks, verification status
- `exec-log.jsonl`: Append-only structured execution log (JSONL)
- `verification-evidence.jsonl`: Test/build/lint/typecheck results
- `snapshots/`: Timestamped state snapshots for `/workflow-resume`

### Self-Evolution

- **skill-detector.py** auto-detects new skill needs from unmatched tasks (3+ similar occurrences)
- **rule-evaluator.py** accumulates rules from corrections; sentinel checks violations during review

## Conventions

- **Shell scripts** must use LF line endings (enforced by `.gitattributes`: `*.sh text eol=lf`)
- **Agent/command/skill files** are markdown with YAML frontmatter (`---` delimited)
- **Subagent prompts** must include full context directly — never let subagents read plan files themselves
- **Test-first** is mandatory for behavior changes (RED → GREEN → REFACTOR)
- **Review is two-stage**: spec compliance first, code quality second — never reverse the order
- **Verification evidence**: Never claim completion without fresh test/build/lint evidence recorded by hooks
- **Plugin installation**: `/plugin marketplace add hgl-pong/claude-code-flow` then `/plugin install` then `/reload-plugins`
