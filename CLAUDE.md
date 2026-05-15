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
- **Opus xhigh** (oracle): Planning, architecture, system decomposition, UI design decisions
- **Sonnet high** (forge, prism, sentinel): Implementation, testing/acceptance, review
- **Haiku** (artist): Image generation

Research is handled by the `research` skill — dispatched as general-purpose subagents with inlined methodology. No dedicated research agent needed. **Never use `subagent_type: "claude-code-flow:research"` — always use `subagent_type: "general-purpose"`.**

UI design is handled by the `ui-design` skill (not a separate agent). Oracle decides during planning whether to invoke it for frontend-UI tasks.

`sentinel` is the only READ-ONLY agent — it produces review reports, never modifies code.

### Workflow Pipeline

```
Plan + Architecture (oracle) → Implementation (forge) → Testing + Acceptance (prism) → Review (sentinel)
```

When work references another repo, plugin, agent pack, or external workflow, run `workflow-intake` before oracle planning. It produces an Adopt / Adapt / Reject / Defer intake record so outside ideas strengthen this workflow without importing a competing ECC-style surface.

`/plan` is the plugin planning entry; `EnterPlanMode` is guarded so model-triggered built-in plan mode redirects back to the plugin workflow. Host-level plan transitions such as Shift+Tab or SDK permission-mode changes cannot be fully intercepted by a plugin.

`dev-orchestrator` is the default execution skill once the user asks to implement, execute an approved plan, coordinate agents, touch multiple files, or deliver an end-to-end change. It should trigger more readily than individual execution guidance because it owns the full plan→implementation→test→review handoff.

Modes (`quick/standard/deep/autonomous/ultrawork`) control which gates are enforced. The pipeline is orchestrated by the `dev-orchestrator` skill using Claude Code's built-in `TaskCreate/TaskList/TaskUpdate` for task management.

### Autonomous Modes

- **ULW (Ultrawork)**: Single-task full-autonomous execution. A stop hook (`ulw-stop-hook.sh`) blocks exit until `<ulw-done>` is emitted in the transcript.
- **ULI (Ultra Loop Iteration)**: Product iteration loop with PD agent proposing requirements each cycle. Stop hook blocks until `<uli-done>`.

### Hook System (13 event types)

All hooks registered in `hooks/hooks.json`, scripts in `hooks/scripts/`. Scripts use `${CLAUDE_PLUGIN_ROOT}` for portable paths. Key hooks:
- **PreToolUse(Bash)**: Commit guard — blocks `git commit` when unreviewed files exist
- **PreToolUse(Agent)**: Agent guard — blocks sentinel only when no review target is available from workflow-tracked files, git changes, explicit file/directory targets, diff context, or document `review_focus`
- **PreToolUse(EnterPlanMode)**: Plan guard — blocks built-in plan-mode tool calls and redirects to plugin `/plan`
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
- **img-cli**: Installed from `vendor/img-cli` submodule via `pip install -e vendor/img-cli`. Artist agent uses `img generate` and `img describe`.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **claude-code-flow** (542 symbols, 1119 relationships, 23 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/claude-code-flow/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/claude-code-flow/context` | Codebase overview, check index freshness |
| `gitnexus://repo/claude-code-flow/clusters` | All functional areas |
| `gitnexus://repo/claude-code-flow/processes` | All execution flows |
| `gitnexus://repo/claude-code-flow/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
