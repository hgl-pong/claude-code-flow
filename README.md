# Claude Code Flow

Claude Code Flow is a shared Claude Code and Codex workflow plugin for multi-step software delivery. It provides curated skills, model-tiered agent prompts, hook-driven workflow state, and local regression tests.

## Core Ideas

- **Shared plugin root:** Claude Code and Codex use the same `skills/`, `agents/`, `hooks/scripts/`, and `commands/` directories.
- **Structured plan state:** planning authority lives in `.claude/flow/plan-state.json` and `.claude/flow/workflow-state.json`; `plan_hash` ties exported briefs back to the active plan.
- **Plan mode routing:** `/plan` is the plugin planning entry. Host-level plan transitions such as Shift+Tab or SDK permission-mode changes cannot always be intercepted, so exit host plan mode and rerun `/plan <task>` when needed.
- **Thin entry points:** commands and top-level docs route to authoritative skills and references instead of duplicating complete checklists.
- **Generated hook manifests:** `scripts/render-hooks.py` renders both Claude and Codex hook snapshots.

## Source of Truth

| Topic | Authoritative file |
|---|---|
| Agent roles, models, and behavioral constraints | `agents/*.md` |
| Codex agent metadata overlay | `skills/dev-orchestrator/agents/openai.yaml` references root `agents/` |
| Gate checklist, scheduling, review, and acceptance | `skills/dev-orchestrator/references/pipeline-operations.md` |
| Review command boundaries and sentinel handoff | `skills/dev-orchestrator/references/review.md` |
| Diagnostic command data and output rules | `skills/dev-orchestrator/references/diagnostics.md` |
| Orchestration trigger bias and mode selection | `skills/dev-orchestrator/SKILL.md` |
| Subagent prompt templates | `skills/dev-orchestrator/references/subagent-prompts.md` |
| Slash command entry points | `commands/*.md` as thin routers |
| Runtime workflow state | `.claude/flow/plan-state.json`, `.claude/flow/workflow-state.json` |
| Hook registration | `scripts/render-hooks.py` -> `hooks/hooks.json`, `hooks/codex-hooks.json` |

Top-level docs are navigation. If details conflict, trust the authoritative file in this table.

## Workflow Overview

Agent definitions live only in `agents/*.md`. Gate order, mode behavior, scheduling, review, and acceptance live in `skills/dev-orchestrator/references/pipeline-operations.md`.

Research uses the `research` skill methodology with general-purpose subagents. UI design uses the `design` skill. Review behavior is owned by `agents/sentinel.md` and `skills/dev-orchestrator/references/review.md`.

## Commands

| Command | Purpose |
|---|---|
| `/plan [--mode] <task>` | Start the plugin planning pipeline. |
| `/quick-fix <task>` | Handle a narrow fix without the full planning gate. |
| `/execute-plan <plan>` | Execute an approved implementation plan. |
| `/workflow-resume` | Resume interrupted workflow state. |
| `/code-review [files]` | Run standalone review outside the full pipeline. |
| `/write-tests [target]` | Write or expand tests for a target. |
| `/build-check` | Run build/verification checks. |
| `/workflow-status` | Show current workflow state and diagnostics. |
| `/workflow-timeline` | Show session execution timeline. |
| `/workflow-metrics` | Show session metrics. |
| `/workflow-skills` | Manage or inspect workflow skills. |
| `/ulw <task>` | Single-task autonomous mode. |
| `/uli <goal>` | Product iteration loop. |

## Skills

Skills use progressive disclosure: concise `SKILL.md` files plus `references/` loaded only when needed. Curated workflow skills live under `skills/`; external skills must pass `workflow-intake` before becoming repo-native.

Important entry skills include `dev-orchestrator`, `using-claude-code-flow`, `brainstorming`, `writing-plans`, `testing-strategy`, `code-quality`, `systematic-debugging`, `verification-before-completion`, `design`, and the Figma skill family.

## Workflow References

- Modes, gates, scheduling, review, and acceptance: `skills/dev-orchestrator/references/pipeline-operations.md`
- Review boundaries and fix loops: `skills/dev-orchestrator/references/review.md`
- Diagnostics: `skills/dev-orchestrator/references/diagnostics.md`
- Hook registration: `scripts/render-hooks.py`
- Hook scripts: `hooks/scripts/*`

## Structure

```text
claude-code-flow/
|-- agents/                # shared agent prompt source
|-- commands/              # thin slash-command entry points
|-- skills/                # SKILL.md plus on-demand references
|-- hooks/                 # generated hook manifests plus scripts
|-- scripts/               # shared helper/render scripts
|-- tests/                 # local and optional host E2E regression tests
|-- .claude-plugin/        # Claude Code plugin manifest
`-- .codex-plugin/         # Codex plugin manifest
```

## Installation

### Required

```bash
npm install -g gitnexus
gitnexus analyze .
```

### Optional

```bash
cd vendor/img-cli && pip install -e . && cd ../..
```

### Claude Code plugin

```text
/plugin marketplace add hgl-pong/claude-code-flow
/plugin install claude-code-flow@claude-code-flow
/reload-plugins
```

```cmd
claude plugin uninstall claude-code-flow@claude-code-flow
claude plugin marketplace remove claude-code-flow
claude plugin marketplace add hgl-pong/claude-code-flow
claude plugin install claude-code-flow@claude-code-flow
```

### Codex plugin

The repository root is also a Codex plugin. Following the Superpowers-style layout, Claude Code and Codex share the same root `skills/` and `agents/` directories instead of maintaining host-specific copies.

Codex reads `.codex-plugin/plugin.json`, loads `skills/`, uses `hooks/codex-hooks.json`, and picks up Playwright MCP configuration from `.mcp.json`.

Codex-specific agent metadata lives beside the owning skill at `skills/dev-orchestrator/agents/openai.yaml`; it references the root `agents/` roster rather than duplicating agent prompts.

For local Codex app discovery, use the repo marketplace at:

```text
.agents/plugins/marketplace.json
```

## Statusline

The statusline shows model, project, git branch, context usage, optional cost and rate-limit data, workflow phase, task progress, and verification status.

It is installed automatically by the Claude Code `SessionStart` hook. To configure manually, edit `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash /path/to/claude-code-flow/scripts/statusline.sh"
  }
}
```

## Testing

```bash
python tests/run-tests.py
python -m unittest tests.test_plugin_integrity
bash tests/claude-code/run-e2e-tests.sh
```
