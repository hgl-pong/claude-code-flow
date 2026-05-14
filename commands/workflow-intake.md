---
name: workflow-intake
description: "Selectively inspect an external repo, plugin, agent pack, or workflow and decide what to adopt, adapt, reject, or defer for Claude Code Flow."
---

# Workflow Intake

Run a selective intake pass before changing this workflow based on an outside source.

## Arguments

```
/workflow-intake <source repo/path/url> [goal]
```

## Process

1. Use `workflow-intake` skill.
2. Inspect only the source areas relevant to the goal.
3. Classify source ideas by surface: agents, skills, commands, hooks, rules, docs, runtime.
4. For every candidate, choose Adopt / Adapt / Reject / Defer.
5. Prefer strengthening existing `oracle`, `forge`, `prism`, `sentinel`, skill, command, hook, or verification lanes over adding new parallel surfaces.
6. Write `<output_dir>/intake-decision.md` for standard/deep/autonomous workflow changes.
7. Hand accepted/adapted ideas to `/plan`; rejected ideas stay documented and are not ported.

## Guardrails

- Do not import a full external agent catalog.
- Do not add a new runtime, daemon, installer, or control plane unless the user explicitly approves a separate design.
- Do not duplicate an existing skill or command when a thin update to the existing surface is enough.
- Do not commit generated, imported, or learned skills into `skills/`; curated repo skills must be intentionally authored.

## Usage

```
/workflow-intake https://github.com/example/agent-pack improve planning and review gates
```
