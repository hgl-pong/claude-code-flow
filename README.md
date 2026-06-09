# Claude Code Flow

Claude Code Flow is a software development methodology for your coding agents, built on top of composable skills that trigger automatically at the right moments.

## Quickstart

Give your agent Claude Code Flow: [Claude Code](#claude-code), [Codex CLI](#codex-cli), [Codex App](#codex-app).

## How it works

It starts from the moment you fire up your coding agent. As soon as it sees that you're building something, it *doesn't* just jump into writing code. Instead, it steps back and asks you what you're really trying to do.

Once it's teased a spec out of the conversation, it shows it to you in chunks short enough to actually read and digest.

After you've signed off on the design, your agent puts together an implementation plan clear enough for an enthusiastic junior engineer with poor taste, no judgment, no project context, and an aversion to testing to follow. It emphasizes true red/green TDD, YAGNI (You Aren't Gonna Need It), and DRY.

Next up, once you say "go", it launches a *workflow-driven-development* process, dispatching agents to work through each engineering task, inspecting and reviewing their work, and continuing forward. It's not uncommon for Claude to be able to work autonomously for a couple hours at a time without deviating from the plan.

There's a bunch more to it, but that's the core of the system. And because the skills trigger automatically, you don't need to do anything special. Your coding agent just has Claude Code Flow.

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

1. **auto-mode** — Fully autonomous research, multi-agent brainstorming, spec, plan, implementation, reviews, gates, and finalization.

2. **semi-auto** — Human-approved discovery/spec/plan, then dynamic workflow execution with built-in review and verification gates.

3. **using-git-worktrees** — Creates isolated workspace on new branch, runs project setup, verifies clean test baseline.

4. **finishing-a-development-branch** — Verifies tests, presents options (merge/PR/keep/discard), cleans up worktree.

**The agent checks for relevant skills before any task.** Mandatory workflows, not suggestions.

## What's Inside

### Skills Library

**Orchestration**
- **auto-mode** — Fully autonomous dynamic workflow.
- **semi-auto** — Human-approved planning followed by dynamic workflow execution.

**Debugging**
- **systematic-debugging** — 4-phase root cause process (includes root-cause-tracing, defense-in-depth, condition-based-waiting techniques).

**Workflow Support**
- **using-git-worktrees** — Parallel development branches.
- **finishing-a-development-branch** — Merge/PR decision workflow.
- **image-generation** — Image generation/editing via artist workflow.

**Meta**
- **using-claude-code-flow** — Bootstrap that teaches the agent how to find and use skills.

### Hooks

PreToolUse hooks intercept tool calls before execution:

| Hook | Matcher | Purpose |
|---|---|---|
| `plan-mode-guard.py` | `EnterPlanMode` | Routes plan mode through the skill pipeline |
| `9router-intercept.py` | `WebSearch\|WebFetch\|...` | Intercepts web search/fetch for routing |

Hook manifests are generated from `scripts/render-hooks.py`. Edit the registry there, then run:

```bash
python scripts/render-hooks.py claude --write
python scripts/render-hooks.py codex --write
```

### Statusline

`scripts/statusline.sh` produces a compact session status bar showing model, directory, git branch, context usage, cost, and rate limits. Self-contained — no dependency on hook scripts.

## Philosophy

- **Test-Driven Development** — Write tests first, always
- **Systematic over ad-hoc** — Process over guessing
- **Complexity reduction** — Simplicity as primary goal
- **Evidence over claims** — Verify before declaring success

## Contributing

The general contribution process is below. Keep in mind that we don't generally accept contributions of new skills and that any updates to skills must work across all supported coding agents.

1. Fork the repository
2. Create a branch for your work
3. Use `semi-auto` to create a spec/plan and capture eval evidence for skill changes
4. Submit a PR, being sure to fill in the pull request template
