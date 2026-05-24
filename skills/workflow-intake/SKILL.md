---
name: workflow-intake
description: "Intake external repos, plugins, agent packs, workflows, prompt systems, or optimization ideas before adapting them into this workflow. Use when referencing, borrowing, porting, importing, copying, comparing, or optimizing from an external workflow source."
---

# Workflow Intake

Adapt useful external ideas without importing a competing workflow surface.

## Iron Law

Do not wholesale-import external workflows. Each candidate must be Adopt, Adapt, Reject, or Defer with a reason.

## Workflow

1. Identify source, scope, and intended benefit.
2. Inspect only the relevant external artifacts.
3. Map ideas to existing Claude Code Flow lanes: agents, skills, commands, hooks, references, tests.
4. Decide Adopt / Adapt / Reject / Defer.
5. Record decisions when they affect planning.
6. Hand approved changes to planning/dev-orchestrator.

## Decision Record

When intake affects implementation, create/update `intake-decision.md` with:

- Source
- Candidate idea
- Decision
- Rationale
- Native destination
- Risks / verification

## Intake Decision Artifact

For workflow/plugin references, produce intake-decision.md before planning. Each candidate idea must be classified Adopt / Adapt / Reject / Defer, grouped by agents, skills, commands, hooks, rules, docs, or runtime. Do not import a full external agent catalog; prefer strengthening existing surfaces.

## Surface Duplication Guard

Adopt strengthens existing surfaces instead of adding rival workflow lanes. Adapt narrows useful source behavior into existing agents, skills, commands, hooks, rules, docs, or runtime state. Reject creates a documented non-goal with rationale so rejected ideas are not re-imported later.
