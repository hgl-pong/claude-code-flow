# Subagent Prompt Templates

Templates for dispatching agents in the CCF pipeline. Paste full task text — never make subagents read plan files. Every dispatch must include a Handoff Artifact schema so completion can be verified without trusting agent prose.

## Agentic Default Rule

The main conversation implements directly only for very lightweight tasks: changing only a few lines, touching 1-2 files, or adding 1-2 small files with obvious scope. Heavy work uses the full flow when it likely touches more than 5 files, creates more than 3 files, spans broad behavior/workflow/prompt/hook/test changes, changes architecture/UI, feels unfamiliar/quality-sensitive, or asks for a website, official site, landing page, docs site, design system website, or multi-page UI. Otherwise the main conversation decomposes work, builds self-contained envelopes, dispatches role-specific subagents, checks returned artifacts against scope, records evidence, and performs final reporting.

## Long-Task Harness Rules

For team-backed work, every prompt must include `team_name`, `taskId`, expected owner name, file scope, blocked dependencies already completed, and whether the agent may claim more tasks. Default: agents complete only the assigned task, request the TaskList update in their Handoff Artifact, then stop and report. The orchestrator validates scope/evidence and performs `TaskUpdate`. The orchestrator alone creates/shuts down teams, changes dependency structure, dispatches newly unblocked waves, and decides final completion.

Use `SendMessage` only for bounded corrections or clarifying blockers. Do not use peer chat as the handoff channel; durable state is TaskList plus Handoff Artifact.

## Handoff Artifact

All agents return this block exactly once:

```markdown
## Handoff Artifact
- Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED | REJECT
- Scope completed: <requirements satisfied or not>
- Files read: <exact paths>
- Files modified: <exact paths, or N/A>
- Evidence: `<command>` -> <pass/fail/unknown + key output>
- Next owner: orchestrator | oracle | forge | prism | sentinel | user
- TaskList update: <status changed / not changed + reason>
- Open risks: <specific risks, or "none">
```

## Forge (Implementer)

```
Agent({
  description: "Implement Task N: [task name]",
  subagent_type: "claude-code-flow:forge",
  model: "sonnet",
  run_in_background: true,
  prompt: """
## Task Description

[FULL TEXT of task from plan — paste it here]

## Harness Coordination

- team_name: <team name, or N/A - not team-backed>
- taskId: <task id, or N/A - not team-backed>
- expected owner: <agent name>
- file scope: <exact files allowed for this task>
- completed dependencies: <blocking task outputs already complete>
- may claim more tasks: no unless orchestrator explicitly says yes

## Context

[Where this fits, dependencies, architectural context, completed prior tasks]

## Your Job

1. Implement exactly what the task specifies
2. Write tests (TDD: write failing test → implement → verify pass)
3. Self-review before reporting
4. Return the Handoff Artifact exactly once

Work from: [directory]

**While you work:** If you encounter something unexpected or unclear, report NEEDS_CONTEXT. Don't guess.

## Self-Review Checklist

- Did I fully implement everything in the spec?
- Did I avoid overbuilding (YAGNI)?
- Did I follow existing patterns in the codebase?
- Do tests verify behavior (not just mock behavior)?

## FILES_MODIFIED (required on completion)
List ALL files created or modified.

## Handoff Artifact

- Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- Scope completed: <requirements satisfied or not>
- Files read: <exact paths>
- Files modified: <exact paths, or N/A>
- Evidence: `<command>` -> <pass/fail/unknown + key output>
- Next owner: orchestrator | prism | sentinel | user
- TaskList update: <status changed / not changed + reason>
- Open risks: <specific risks, or "none">
"""
})
```

## Sentinel Stage 1 (Spec Compliance)

```
Agent({
  description: "Spec compliance review for Task N",
  subagent_type: "claude-code-flow:sentinel",
  model: "sonnet",
  run_in_background: true,
  prompt: """
Review whether implementation matches specification. READ-ONLY — do not modify any files.

## Harness Coordination

- team_name: <team name, or N/A - not team-backed>
- taskId: <task id, or N/A - not team-backed>
- expected owner: <agent name>
- file scope: <exact files to review>
- completed dependencies: <implementation/verification outputs already complete>
- may claim more tasks: no

## What Was Requested

[FULL TEXT of task requirements]

## What Was Implemented

[From forge's report — but DO NOT trust it. Verify independently by reading actual code.]

## Your Job

Read the actual code and verify:

**Missing:** Did they implement everything requested? Any skipped requirements?
**Extra:** Did they build things not requested? Over-engineer?
**Misunderstandings:** Different interpretation of requirements?

**Verify by reading code, not by trusting the report.**

## Handoff Artifact

- Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED | REJECT
- Scope completed: <spec compliant, or missing/extra work>
- Files read: <exact paths>
- Files modified: N/A
- Evidence: `read-only review` -> <pass/fail + key file:line evidence>
- Next owner: orchestrator | forge | user
- TaskList update: not changed - read-only review
- Open risks: <specific risks, or "none">
"""
})
```

## Sentinel Stage 2 (Code Quality)

Only dispatch AFTER Stage 1 passes.

```
Agent({
  description: "Code quality review for Task N",
  subagent_type: "claude-code-flow:sentinel",
  model: "sonnet",
  run_in_background: true,
  prompt: """
Code quality review. READ-ONLY — do not modify any files.

## Harness Coordination

- team_name: <team name, or N/A - not team-backed>
- taskId: <task id, or N/A - not team-backed>
- expected owner: <agent name>
- file scope: <exact files to review>
- completed dependencies: <spec review output already complete>
- may claim more tasks: no

## Scope

BASE_SHA: [commit before task]
HEAD_SHA: [current commit]

## Review Focus

- Does each file have one clear responsibility?
- Are units decomposed for independent understanding and testing?
- Are names clear and accurate?
- Any code smells, security issues, or performance concerns?

## Handoff Artifact

- Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED | REJECT
- Scope completed: <quality approved, or issues found>
- Files read: <exact paths>
- Files modified: N/A
- Evidence: `read-only review` -> <pass/fail + key file:line evidence>
- Next owner: orchestrator | forge | user
- TaskList update: not changed - read-only review
- Open risks: <specific risks, or "none">
"""
})
```

## Prism (Testing / Acceptance)

```
Agent({
  description: "Acceptance testing for Task N",
  subagent_type: "claude-code-flow:prism",
  model: "sonnet",
  run_in_background: true,
  prompt: """
## Harness Coordination

- team_name: <team name, or N/A - not team-backed>
- taskId: <task id, or N/A - not team-backed>
- expected owner: <agent name>
- file scope: <exact files/tests allowed for this task>
- completed dependencies: <forge/review outputs already complete>
- may claim more tasks: no

## Task

[FULL TEXT of acceptance criteria from plan]

## Forge's Report

[From implementer's FILES_MODIFIED and verification output]

## Your Job

1. Read the plan requirements and forge's changes
2. Run the specified test commands
3. Verify behavior matches acceptance criteria
4. Run broader regression if applicable

## Handoff Artifact

- Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED | REJECT
- Scope completed: <accepted, or rejected with reason>
- Files read: <exact paths>
- Files modified: <exact paths, or N/A>
- Evidence: `<command>` -> <pass/fail + key output>
- Next owner: orchestrator | forge | sentinel | user
- TaskList update: <status changed / not changed + reason>
- Open risks: <specific risks, or "none">
"""
})
```

## Research (general-purpose subagent)

**WARNING**: Research is NOT an agent type. Always use `subagent_type: "general-purpose"` with research methodology inlined in the prompt. NEVER use `subagent_type: "claude-code-flow:research"` — that type does not exist.

Research is dispatched as a **general-purpose** subagent using the `research` skill methodology.
See `skills/research/references/dispatch-templates.md` for dispatch templates (Technical Research, UI Research, Product Analysis).

Key rules:
- Research and oracle are STRICTLY SEQUENTIAL — never dispatch oracle until research finishes.
- Research is read-only — multiple research subagents can run in parallel with no conflict.
