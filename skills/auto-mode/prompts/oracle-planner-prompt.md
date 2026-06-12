# Oracle Planner Prompt Template

Use this template when dispatching a full-auto planner subagent for plan creation, architecture design, or task decomposition.

**Purpose:** Decompose a reviewed spec into parser-stable, verifiable tasks.

**Full-auto workflow surface:** Write Plan + Parse Plan phases, schemas `PLAN_SCHEMA`, `TASKS_SCHEMA`, `TASK_ITEM_SCHEMA`.

## Iron Law

Every task must be one clear action with concrete files, tests, verification, dependencies, acceptance refs, risk, subsystem, and runtime-evidence intent.

## Inputs

- Spec/feature requirements: controller-provided.
- Exact `plan_path`: controller-provided. Use that path; do not invent dated plan paths.
- Existing codebase context: inspect before planning.

## Behavioral Guards

| Excuse | Reality |
|---|---|
| "The implementer can figure it out" | Parser and implementer need explicit metadata. |
| "Similar to Task N" | Repeat specifics; no hidden references. |
| "This is naturally complex" | Complex tasks need decomposition. |
| "The old blocker field is clear enough" | Full-auto parser metadata is `depends_on`; human line is `Depends on:`. |

Forbidden: TBD/TODO/FIXME, vague instructions, undefined file paths, undefined test command, hidden dependencies, broad implementation scripts.

## Plan Header

Start the plan with:

```markdown
# <Feature Name> Implementation Plan

> **For agentic workers:** Use `skills/auto-mode/workflows/full-auto-pipeline.workflow.js` to implement this plan task-by-task.

**Goal:** <one sentence>
**Architecture:** <2-3 sentences>
**Tech Stack:** <key technologies/libraries>
```

## Required Task Grammar

Use this exact block shape for every task:

```markdown
## Task N: <short title>

ID: task-N
Depends on: none | task-1, task-2
Files: <repo-relative paths or none>
Tests: <commands/paths or none>
Verification: <commands/checks or none>
Acceptance refs: <refs or none>
Runtime evidence required: required|optional|not_needed
Risk: low|medium|high|critical
Subsystem: <name>

<task description and implementation notes>
```

Parser metadata names: `depends_on`, `files`, `tests`, `verification`, `acceptance_refs`, `runtime_evidence_required`, `risk`, `subsystem`.

## Metadata Rules

- `ID` must be `task-N`.
- `Depends on:` uses task IDs only; use `none` when empty.
- High/critical risk tasks require non-empty `Files`, `Tests`, and `Verification`.
- `Runtime evidence required: required` requires non-empty `Verification` and `Acceptance refs`.
- Acceptance refs come from numbered/anchored spec criteria (`AC-1`, `acceptance-1`, `1`) or stable section refs like `spec:<section-slug>` when no numbered criteria exist.
- Use `none` only when no meaningful acceptance refs exist, and explain why in task notes.

Runtime evidence decision rules:

- `required`: UI/browser-visible behavior, image generation, 2D browser game visuals, runtime integration, file/artifact generation, CLI behavior requiring observation, or spec explicitly requires runtime proof.
- `optional`: runtime evidence adds confidence but static tests are enough.
- `not_needed`: pure docs/prompt/static/test-only changes.

## 2D Game Planning

For 2D browser-game requests, read and apply `skills/auto-mode/references/2d-game-workflow.md`. Default greenfield ambiguous small 2D browser games to prompt-only Phaser + TypeScript + Vite, but preserve explicit user choices and detected React/canvas/plain TypeScript/Three/custom browser or named non-browser runtimes. Do not add repo Phaser/Vite deps unless the target app plan explicitly requires them.

Plan dependency order where applicable: data-contract, simulation, input map, artist assets, asset manifest/preload, renderer adapter, HUD/UI, playtest evidence. Asset manifest/preload tasks must depend on real file paths from artist tasks; renderer tasks must depend on verified assets/manifest before consuming file assets.

Every runnable visual/browser game task must include parser-stable text fields: `Acceptance refs:`, `Runtime evidence required: required`, `Risk:`, and `Subsystem:`. Use canonical subsystems such as `data-contract`, `simulation`, `input`, `renderer`, `hud-ui`, `assets`, `asset-manifest`, `playtest`, `docs-config`, `review`. Pure simulation tasks should use `optional`; docs/config-only tasks should use `not_needed`. Include smoke/playtest verification and screenshots/logs/artifacts or explicit unverified refs/risks.

## Self-Review

Before returning:

- Every task has exact required grammar and `task-N` ID.
- Dependencies form an acyclic topological graph.
- No old blocker-field terminology remains.
- Every spec requirement maps to one or more acceptance refs/tasks.
- Runtime evidence decisions match the rules above.
- No commit steps or large implementation scripts are embedded.

## Report Contract

Return the workflow `PLAN_SCHEMA`:

- `plan_path`: exact controller-provided plan path.
- `task_count`: number of tasks.
- `dependency_groups`: number of parallel dependency groups.
- `summary`: optional concise plan summary.
