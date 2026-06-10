# Claude Code Flow

Claude Code Flow is a software development methodology for coding agents centered on one primary workflow skill: auto-mode.

## Quickstart

Give your agent Claude Code Flow: [Claude Code](#claude-code), [Codex CLI](#codex-cli), [Codex App](#codex-app).

## How it works

Auto-mode runs the whole development loop: understand the request, inspect the codebase, produce a spec/plan when needed, implement, review, verify, and finalize locally. Routine decisions are inferred and logged; the agent stops only when requirements genuinely need human input.

Image generation is not a separate workflow. When a task needs images, sprites, mockups, or edited assets, auto-mode dispatches focused image work and consumes the returned files/manifests only after they exist.

## Installation

### Claude Code

- Register the marketplace:

  ```bash
  /plugin marketplace add hgl-pong/claude-code-flow
  ```

- Install the plugin:

  ```bash
  /plugin install claude-code-flow@claude-code-flow
  ```

Reinstall from scratch:

  ```bash
  claude plugin uninstall claude-code-flow@claude-code-flow
  claude plugin marketplace remove claude-code-flow
  claude plugin marketplace add hgl-pong/claude-code-flow
  claude plugin install claude-code-flow@claude-code-flow
  ```

### Codex CLI

- Register the marketplace:

  ```bash
  /plugin marketplace add https://github.com/hgl-pong/claude-code-flow
  ```

- Install the plugin:

  ```bash
  /plugin install claude-code-flow@claude-code-flow
  ```

### Codex App

- In the Codex app, click on Plugins in the sidebar.
- Add the marketplace: `https://github.com/hgl-pong/claude-code-flow`
- Search for `claude-code-flow` and click `+` to install.

## The Basic Workflow

1. **auto-mode** — Fully autonomous discovery, planning, implementation, reviews, gates, finalization, and conditional image generation.
2. **systematic-debugging** — Structured root-cause debugging with defense-in-depth fixes and condition-based waiting.

## What's Inside

### Skills Library

**Orchestration**
- **auto-mode** — Primary Claude Code Flow development workflow.

**Debugging**
- **systematic-debugging** — 4-phase root cause process with root-cause tracing, defense-in-depth, and condition-based waiting techniques.

### Hooks

Hooks provide guardrails for planning, web routing, and active auto-mode runtime state. Startup injection is not required.

| Hook | Matcher | Purpose |
|---|---|---|
| `plan-mode-guard.py` | `EnterPlanMode` | Routes plan mode through the workflow guardrail |
| `9router-intercept.py` | `WebSearch\|WebFetch\|...` | Intercepts web search/fetch for routing |
| `auto-mode-hooks.py` | `Stop`, `SubagentStart`, `SubagentStop`, `PreCompact`, `TeammateIdle` | Protects active auto-mode state |

Hook manifests are generated from `scripts/render-hooks.py`. Edit the registry there, then run:

```bash
python scripts/render-hooks.py claude --write
python scripts/render-hooks.py codex --write
```

### Statusline

`scripts/statusline.sh` produces a compact session status bar showing model, directory, git branch, context usage, cost, and rate limits. Self-contained — no dependency on hook scripts.

## Philosophy

- **Test-Driven Development** — Write tests first when useful and verifiable
- **Systematic over ad-hoc** — Process over guessing
- **Complexity reduction** — Simplicity as primary goal
- **Evidence over claims** — Verify before declaring success

## Contributing

The general contribution process is below. We generally do not accept new standalone skills; workflow capabilities should usually belong inside auto-mode unless they are broadly useful debugging techniques.

1. Fork the repository
2. Create a branch for your work
3. Use `auto-mode` to create a spec/plan and capture eval evidence for skill changes
4. Submit a PR, being sure to fill in the pull request template
