// Invoked by the workflow-driven-development skill via:
//   Workflow({ script: <this file>, args: { groups, tasks, worktree, model_tasks } })
//
// Each agent prompt is built inline from the task data — the behavioral guards,
// self-review checklists, and adversarial review stances come from the canonical
// prompt templates (implementer-prompt.md, spec-reviewer-prompt.md, etc.).
//
// See SKILL.md for step-by-step launch instructions.

export const meta = {
  name: 'execute-plan',
  description:
    'Execute implementation plan tasks — implement, spec review, code quality review — with dependency-aware pipeline orchestration',
  phases: [
    { title: 'Implement', detail: 'Implement tasks within dependency groups in parallel' },
    { title: 'Spec Review', detail: 'Verify each task matches its requirements' },
    { title: 'Code Review', detail: 'Review code quality for each task' },
    { title: 'Final Review', detail: 'Cross-task code review' },
  ],
}

const { groups, tasks, worktree, model_tasks } = args
const MAX_RETRIES = 5

// ── Structured Output Schemas ─────────────────────────────────────────

const IMPLEMENT_RESULT = {
  type: 'object',
  additionalProperties: false,
  properties: {
    status: { type: 'string', enum: ['DONE', 'DONE_WITH_CONCERNS', 'BLOCKED'] },
    summary: { type: 'string', description: 'What was implemented and how' },
    files_modified: { type: 'array', items: { type: 'string' }, description: 'Every file created or changed' },
    test_results: { type: 'string', description: 'Test command and output' },
    commit_sha: { type: 'string', description: 'Git commit SHA (short)' },
    concerns: { type: 'array', items: { type: 'string' }, description: 'If DONE_WITH_CONCERNS, list each concern' },
    blocker_detail: { type: 'string', description: 'If BLOCKED: what blocks you, what you tried' },
  },
  required: ['status', 'summary', 'files_modified'],
}

const REVIEW_RESULT = {
  type: 'object',
  additionalProperties: false,
  properties: {
    passed: { type: 'boolean' },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: false,
        properties: {
          severity: { type: 'string', enum: ['Critical', 'Important', 'Minor'] },
          file: { type: 'string' },
          line: { type: 'number' },
          description: { type: 'string' },
        },
        required: ['severity', 'description'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['passed', 'issues', 'summary'],
}

// ── Agent options helper ──────────────────────────────────────────────

function opts(label, phase, schema) {
  const o = { label, phase, schema }
  if (model_tasks) o.model = model_tasks
  return o
}

// ── Prompt builders — drawn from implementer-prompt.md, spec-reviewer-prompt.md,
//    code-quality-reviewer-prompt.md, with structured output requirements ─

function implementPrompt(task) {
  return `You are implementing ${task.id}. Work from: ${worktree}

## Task Description

${task.description}

## Self-Service

You work independently. If something is unclear:
1. Search the codebase for existing patterns and conventions
2. Infer the right approach from how similar things are done
3. Pick the simplest approach that fits the requirements
4. Record any assumptions in the concerns field

## Behavioral Guards

| Excuse | Reality |
|--------|---------|
| "Tests can come later" | Tests verify correctness. Later means never. |
| "This is too simple to break" | Simple code breaks. A 30-second test prevents a 3-hour debug. |
| "I'll refactor while I'm here" | Refactoring outside scope is scope creep. Ship the task. |
| "I'll add a TODO for the edge case" | TODOs rot. Handle edge cases or record them as concerns. |

## Process

1. Read existing code for conventions and patterns
2. Write failing test first (for behavior changes)
3. Implement only what the task specifies — no scope creep
4. Run tests, verify GREEN
5. Commit with: feat(${task.id}): [what you built]
6. Self-review before reporting (see below)

## Code Organization

- Follow the file structure defined in the task
- Each file should have one clear responsibility with a well-defined interface
- If a file is growing beyond the task's intent, stop and note it as a concern
- In existing codebases, follow established patterns. Improve code you touch, but don't restructure things outside your task

## When You're in Over Your Head

It is always OK to stop and say "this is too hard for me." Bad work is worse than no work.

STOP and escalate when:
- The task requires architectural decisions with multiple valid approaches
- You need to understand code beyond what was provided and can't find clarity
- You feel uncertain about whether your approach is correct
- The task involves restructuring existing code in ways the plan didn't anticipate
- You've been reading file after file trying to understand the system without progress

How to escalate: Report BLOCKED. Describe specifically what you're stuck on, what you've tried, and what kind of help you need.

## Before Reporting Back: Self-Review

Completeness:
- Did I fully implement everything in the spec?
- Did I miss any requirements?
- Are there edge cases I didn't handle?

Quality:
- Is this my best work?
- Are names clear and accurate (describe WHAT, not HOW)?
- Is the code clean and maintainable?

Discipline:
- Did I avoid overbuilding (YAGNI)?
- Did I only build what was requested?

Testing:
- Do tests actually verify behavior (not mock behavior)?
- Did I follow TDD if required?

If you find issues during self-review, fix them now before reporting.

## Structured Output

Your final response will be parsed as JSON. You MUST return valid JSON.`
}

function specReviewPrompt(task, impl) {
  return `Verify whether the implementation matches its specification.

## What Was Requested

${task.description}

## What The Implementer Claims

${impl.summary}

Files changed: ${impl.files_modified.join(', ')}

## CRITICAL: Do Not Trust the Report

The implementer may have finished suspiciously quickly. Their report may be
incomplete, inaccurate, or optimistic. You MUST verify everything independently.

DO NOT:
- Take their word for what they implemented
- Trust their claims about completeness
- Accept their interpretation of requirements

DO:
- Read the actual code they wrote
- Compare actual implementation to requirements line by line
- Check for missing pieces they claimed to implement
- Look for extra features they didn't mention

## What to Check

Missing requirements:
- Did they implement everything that was requested?
- Are there requirements they skipped or missed?
- Did they claim something works but didn't actually implement it?

Extra/unneeded work:
- Did they build things that weren't requested?
- Did they over-engineer or add unnecessary features?
- Did they add "nice to haves" that weren't in the spec?

Misunderstandings:
- Did they interpret requirements differently than intended?
- Did they solve the wrong problem?

## Severity

Use Critical for: missing required functionality, wrong behavior, broken requirements.
Use Important for: scope creep, extra features not in spec.
Use Minor for: edge cases not covered, spec ambiguity.

## Structured Output

Your final response will be parsed as JSON. You MUST return valid JSON.`
}

function codeReviewPrompt(impl, taskId) {
  return `Review the implementation for code quality.

## Context

Task: ${taskId}
Summary: ${impl.summary}
Files: ${impl.files_modified.join(', ')}

## Instructions

Read the actual code in the changed files. Evaluate:

Cleanliness:
- Are names clear and accurate (describe WHAT, not HOW)?
- Is there dead code, duplicate logic, or unnecessary abstraction?
- Are there magic numbers that should be named constants?

Correctness:
- Do tests verify real behavior (not just mock behavior)?
- Are edge cases and error states handled?
- Is there error handling for impossible scenarios (over-engineering)?

Maintainability:
- Does each file have one clear responsibility?
- Are units independently testable?
- Does the implementation follow the plan's file structure?
- Did this change create files that are already large, or significantly grow existing files?

Discipline:
- No overbuilding (YAGNI) — nothing beyond what was requested
- No orphaned imports or unused variables introduced by this change
- Follows existing project conventions
- No commented-out code or TODO markers left behind

Do NOT flag pre-existing issues in files this task touched.
Focus on what this change contributed. Pre-existing file size or
code quality issues are not this implementer's responsibility.

## Severity

Critical: would cause a bug, break the build, or violate a core requirement.
Important: maintainability problems that should be addressed.
Minor: style nits.

## Structured Output

Your final response will be parsed as JSON. You MUST return valid JSON.`
}

function fixPrompt(issues, files) {
  const issuesText = typeof issues === 'string' ? issues : JSON.stringify(issues, null, 2)
  return `Fix the following review issues in the implementation.

## Issues to Fix

${issuesText}

## Files to Modify

${files.join(', ')}

## Instructions

1. Read each file listed above
2. Fix every issue described in the issues list
3. Do NOT make changes beyond fixing these specific issues
4. Do NOT refactor, restructure, or "improve" unrelated code
5. Run the tests to verify nothing broke
6. Commit with: fix(review): address review findings

## Structured Output

Your final response will be parsed as JSON. You MUST return valid JSON.`
}

// ── Self-service escalation rejection ────────────────────────────────

function selfServicePrompt(task) {
  return implementPrompt(task) +
    '\n\n## Escalation Rejected\n\n' +
    'You reported BLOCKED. Re-examine: can you solve this by ' +
    'searching the codebase more thoroughly, picking a simpler ' +
    'approach, or narrowing scope? ' +
    'Only report BLOCKED again if truly impossible.'
}

// ── Main execution ───────────────────────────────────────────────────

const results = { completed: [], blocked: [] }

for (const [gi, group] of groups.entries()) {
  if (group.length === 0) continue
  log('Group ' + (gi + 1) + '/' + groups.length + ': ' + group.length + ' task(s)')

  const groupResults = await parallel(
    group.map(taskId => () => {
      const task = tasks[taskId]

      return pipeline(
        [task],

        // Stage 1: Implement
        async (t) => {
          let result = await agent(implementPrompt(t),
            opts('implement:' + t.id, 'Implement', IMPLEMENT_RESULT))

          if (result && result.status === 'BLOCKED') {
            log(t.id + ': BLOCKED — retrying with self-service prompt')
            result = await agent(selfServicePrompt(t),
              opts('implement:' + t.id + '-r2', 'Implement', IMPLEMENT_RESULT))
          }

          return { ...t, impl: result }
        },

        // Stage 2: Spec Review
        async (ctx) => {
          const { impl, id } = ctx
          if (!impl || impl.status === 'BLOCKED') {
            return { ...ctx, spec_review: null, _blocked: true, _reason: (impl && impl.blocker_detail) || 'BLOCKED' }
          }

          let review = await agent(specReviewPrompt(ctx, impl),
            opts('spec-review:' + id, 'Spec Review', REVIEW_RESULT))

          let iterations = 0
          while (review && !review.passed && iterations < MAX_RETRIES) {
            log(id + ': spec review found ' + (review.issues || []).length + ' issue(s) — fixing')
            const updated = await agent(fixPrompt(review.issues, impl.files_modified),
              opts('fix-spec:' + id, 'Spec Review', IMPLEMENT_RESULT))
            if (updated) ctx.impl = { ...ctx.impl, ...updated }

            review = await agent(specReviewPrompt(ctx, ctx.impl),
              opts('spec-review:' + id + '-r' + (iterations + 1), 'Spec Review', REVIEW_RESULT))
            iterations++
          }

          return {
            ...ctx,
            spec_review: review,
            spec_passed: review ? review.passed : false,
            _iterations_spec: iterations,
          }
        },

        // Stage 3: Code Quality Review
        async (ctx) => {
          if (ctx._blocked || !ctx.spec_passed) return ctx

          let review = await agent(codeReviewPrompt(ctx.impl, ctx.id),
            opts('code-review:' + ctx.id, 'Code Review', REVIEW_RESULT))

          let iterations = 0
          while (
            review &&
            (review.issues || []).some(i => i.severity === 'Critical') &&
            iterations < MAX_RETRIES
          ) {
            const criticals = review.issues.filter(i => i.severity === 'Critical')
            log(ctx.id + ': code review found ' + criticals.length + ' critical issue(s) — fixing')
            const updated = await agent(fixPrompt(criticals, ctx.impl.files_modified),
              opts('fix-code:' + ctx.id, 'Code Review', IMPLEMENT_RESULT))
            if (updated) ctx.impl = { ...ctx.impl, ...updated }

            review = await agent(codeReviewPrompt(ctx.impl, ctx.id),
              opts('code-review:' + ctx.id + '-r' + (iterations + 1), 'Code Review', REVIEW_RESULT))
            iterations++
          }

          return {
            ...ctx,
            code_review: review,
            code_passed: review ? !(review.issues || []).some(i => i.severity === 'Critical') : false,
            _iterations_code: iterations,
          }
        },
      )
    }),
  )

  for (const r of groupResults.flat().filter(Boolean)) {
    if (r._blocked) {
      results.blocked.push({ id: r.id, reason: r._reason, impl: r.impl })
    } else {
      results.completed.push({
        id: r.id,
        spec_passed: r.spec_passed,
        code_passed: r.code_passed,
        code_review: r.code_review,
        files: r.impl ? r.impl.files_modified : [],
      })
    }
  }
}

// ── Final cross-task code review ─────────────────────────────────────

const allPassed = results.completed.length > 0 && results.completed.every(r => r.code_passed)

if (allPassed) {
  phase('Final Review')
  const allFiles = results.completed.flatMap(r => r.files).filter(Boolean)
  const allIds = results.completed.map(r => r.id).join(', ')

  const finalReview = await agent(
    codeReviewPrompt(
      { summary: 'Entire implementation: ' + allIds, files_modified: allFiles },
      'final',
    ),
    opts('final-review', 'Final Review', REVIEW_RESULT),
  )
  results.final_review = finalReview
}

return results
