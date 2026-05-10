# Subagent Prompt Templates

Templates for dispatching agents in the CCF pipeline. Paste full task text — never make subagents read plan files.

## Forge (Implementer)

```
Agent({
  description: "Implement Task N: [task name]",
  subagent_type: "claude-code-flow:forge",
  model: "sonnet",
  prompt: """
## Task Description

[FULL TEXT of task from plan — paste it here]

## Context

[Where this fits, dependencies, architectural context, completed prior tasks]

## Your Job

1. Implement exactly what the task specifies
2. Write tests (TDD: write failing test → implement → verify pass)
3. Commit your work
4. Self-review before reporting

Work from: [directory]

**While you work:** If you encounter something unexpected or unclear, report NEEDS_CONTEXT. Don't guess.

## Self-Review Checklist

- Did I fully implement everything in the spec?
- Did I avoid overbuilding (YAGNI)?
- Did I follow existing patterns in the codebase?
- Do tests verify behavior (not just mock behavior)?

## FILES_MODIFIED (required on completion)
List ALL files created or modified.

## Completion Schema

- **Status:** DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- Files modified:
- Verification (commands run + results):
- RED/GREEN evidence:
- Concerns:
"""
})
```

## Sentinel Stage 1 (Spec Compliance)

```
Agent({
  description: "Spec compliance review for Task N",
  subagent_type: "claude-code-flow:sentinel",
  model: "sonnet",
  prompt: """
Review whether implementation matches specification. READ-ONLY — do not modify any files.

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

Report:
- ✅ Spec compliant
- ❌ Issues found: [list with file:line references]
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
  prompt: """
Code quality review. READ-ONLY — do not modify any files.

## Scope

BASE_SHA: [commit before task]
HEAD_SHA: [current commit]

## Review Focus

- Does each file have one clear responsibility?
- Are units decomposed for independent understanding and testing?
- Are names clear and accurate?
- Any code smells, security issues, or performance concerns?

## Report Format

- **Strengths:** What's done well
- **Issues:** Critical / Important / Minor (with file:line)
- **Assessment:** Approved | Needs fixes
"""
})
```

## Prism (Testing / Acceptance)

```
Agent({
  description: "Acceptance testing for Task N",
  subagent_type: "claude-code-flow:prism",
  model: "sonnet",
  prompt: """
## Task

[FULL TEXT of acceptance criteria from plan]

## Forge's Report

[From implementer's FILES_MODIFIED and verification output]

## Your Job

1. Read the plan requirements and forge's changes
2. Run the specified test commands
3. Verify behavior matches acceptance criteria
4. Run broader regression if applicable

## Report

- **Status:** ACCEPT | REJECT
- Tests run and results:
- Behavioral verification:
- Concerns:
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
