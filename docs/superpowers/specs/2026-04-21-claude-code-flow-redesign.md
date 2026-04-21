# claude-code-flow Redesign

## Goal

Refactor from game-engine-specific plugin to general-purpose development workflow plugin.

## Changes

### Plugin Identity
- Name: `claude-code-flow` (was `game-engine-dev`)
- Description: General-purpose development workflow with model-tiered agents

### Agent Roles (names unchanged)
| Agent | Model | Role | Mode |
|-------|-------|------|------|
| oracle | Opus | Planning, HTML visualization (optional) | Read + Write |
| atlas | Opus | Architecture design | Read-only |
| forge | Sonnet | Code implementation | Read + Write + Edit + Bash |
| prism | Sonnet | Test writing | Read + Write + Edit + Bash |
| anvil | Haiku | Build, CI/CD, dependencies | Read + Write + Edit + Bash |
| sentinel | Sonnet | Code review | Read-only |

### Commands
- `/workflow-plan` — Start planning pipeline
- `/workflow-review` — Start review pipeline
- `/code-review` — Standalone code review
- `/write-tests` — Standalone test writing
- `/build-check` — Standalone build check

### Skills
- `dev-orchestrator` — Main orchestration skill, auto-triggers pipeline
- `code-quality` — General code quality standards
- `testing-strategy` — Testing strategy guide

### Hooks
- SessionStart: Check git status (branch, uncommitted changes, conflicts)
- PostToolUse(Write|Edit): Track modified files for reviewer
- PreToolUse(Bash): Intercept `git commit` for pre-commit review

### Removed
- Game-engine-specific references and skill descriptions
- Agent instructions tied to game engine concepts

### Installation
```
/plugin marketplace add hgl-pong/claude-code-flow
/plugin install claude-code-flow@claude-code-flow
/reload-plugins
```

### Directory Structure
```
claude-code-flow/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── agents/
│   ├── oracle.md
│   ├── atlas.md
│   ├── forge.md
│   ├── prism.md
│   ├── anvil.md
│   └── sentinel.md
├── commands/
│   ├── workflow-plan.md
│   ├── workflow-review.md
│   ├── code-review.md
│   ├── write-tests.md
│   └── build-check.md
├── skills/
│   ├── dev-orchestrator/
│   │   └── SKILL.md
│   ├── code-quality/
│   │   └── SKILL.md
│   └── testing-strategy/
│       └── SKILL.md
└── hooks/
    └── hooks.json
```
