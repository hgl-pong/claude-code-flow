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

### Model-Tiered Agent Pipeline

Agents are markdown files in `agents/` with YAML frontmatter. Each specifies a `model` alias and, for Opus/Sonnet agents, an `effort` level:
- **Opus xhigh** (oracle, atlas): Planning and architecture
- **Opus high** (evolver): Data-backed meta-analysis
- **Sonnet high** (forge, weaver, prism, sentinel, designer): Implementation, testing, review, UI design
- **Sonnet medium** (scout, pd): Research, product proposals
- **Haiku default** (validator, chronicler, anvil): Acceptance checks, docs, build/CI

Some agents are **READ-ONLY** (atlas, sentinel, validator, chronicler, designer) — they produce reports/designs only, never modify code.

### Workflow Pipeline

```
Plan Gate (oracle) → Design Gate (atlas) → Implementation (forge/prism/anvil) → Review Gate (sentinel) → Documentation (chronicler)
```

Modes (`quick/standard/deep/autonomous/ultrawork`) control which gates are enforced. The pipeline is orchestrated by the `dev-orchestrator` skill using Claude Code's built-in `TaskCreate/TaskList/TaskUpdate` for task management.

### Autonomous Modes

- **ULW (Ultrawork)**: Single-task full-autonomous execution. A stop hook (`ulw-stop-hook.sh`) blocks exit until `<ulw-done>` is emitted in the transcript.
- **ULI (Ultra Loop Iteration)**: Product iteration loop with PD agent proposing requirements each cycle. Stop hook blocks until `<uli-done>`.

### Hook System (13 event types)

All hooks registered in `hooks/hooks.json`, scripts in `hooks/scripts/`. Scripts use `${CLAUDE_PLUGIN_ROOT}` for portable paths. Key hooks:
- **PreToolUse(Bash)**: Commit guard — blocks `git commit` when unreviewed files exist
- **PreToolUse(Agent)**: Agent guard — blocks sentinel without modified files
- **PostToolUse(Bash)**: Verification evidence tracking — classifies test/build/lint commands and records results to `verification-evidence.jsonl`
- **PostToolUse(Write/Edit)**: File modification tracking with agent ownership
- **Stop**: ULW/ULI stop hooks block exit until completion tags detected
- **PreCompact/PostCompact**: State preservation across context compaction

### State Machine

Runtime state lives in `.claude/flow/` (gitignored). Key files:
- `workflow-state.json`: Current phase (idle/plan/design/impl/review), mode, tasks, verification status
- `exec-log.jsonl`: Append-only structured execution log (JSONL)
- `verification-evidence.jsonl`: Test/build/lint/typecheck results
- `snapshots/`: Timestamped state snapshots for `/workflow-resume`

### Self-Evolution

- **evolver** agent analyzes `exec-log.jsonl` for failure patterns and proposes prompt improvements
- **skill-detector.py** auto-detects new skill needs from unmatched tasks (3+ similar occurrences)
- **rule-evaluator.py** accumulates rules from corrections; sentinel checks violations during review
- All evolution changes must pass `eval-gate.py` (PASS/WARN/FAIL)

## Conventions

- **Shell scripts** must use LF line endings (enforced by `.gitattributes`: `*.sh text eol=lf`)
- **Agent/command/skill files** are markdown with YAML frontmatter (`---` delimited)
- **Subagent prompts** must include full context directly — never let subagents read plan files themselves
- **Test-first** is mandatory for behavior changes (RED → GREEN → REFACTOR)
- **Review is two-stage**: spec compliance first, code quality second — never reverse the order
- **Verification evidence**: Never claim completion without fresh test/build/lint evidence recorded by hooks
- **Plugin installation**: `/plugin marketplace add hgl-pong/claude-code-flow` then `/plugin install` then `/reload-plugins`
