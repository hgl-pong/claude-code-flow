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

// ── Contract constants (shared with full-auto-pipeline) ────────────────

const RESULT_PARTITIONS = ['passed', 'completed', 'blocked', 'stalled', 'failed_review', 'needs_escalation']

const BLOCKER_TAXONOMY = [
  'agent_output_invalid', 'merge_conflict', 'permissions', 'external_service',
  'tooling_unavailable', 'test_failure', 'runtime_failure', 'dependency_failure',
  'architecture_decision', 'scope_too_large', 'missing_context',
]

const ESCALATION_LADDER = [
  'schema_retry', 'self_service_retry', 'stronger_model',
  'split_subtask', 'enriched_context', 'ask_user',
]

const ESCALATION_ATTEMPTS = {
  schema_retry: 1,
  self_service_retry: 2,
  stronger_model: 1,
  split_subtask: 1,
  enriched_context: 1,
  ask_user: 1,
}

const REVIEW_SEVERITIES = ['Critical', 'High', 'Important', 'Minor', 'Info']
const TASK_RISKS = ['low', 'medium', 'high', 'critical']

const REVIEW_THRESHOLD = {
  spec_review: {
    low:       { Critical: true, High: true, Important: 'if_explicit', Minor: false, Info: false },
    medium:    { Critical: true, High: true, Important: true,          Minor: false, Info: false },
    high:      { Critical: true, High: true, Important: 'if_explicit', Minor: false, Info: false },
    critical:  { Critical: true, High: true, Important: true,          Minor: true,  Info: false },
  },
  code_review: {
    low:       { Critical: true, High: true, Important: 'if_explicit', Minor: false, Info: false },
    medium:    { Critical: true, High: true, Important: true,          Minor: false, Info: false },
    high:      { Critical: true, High: true, Important: 'if_explicit', Minor: false, Info: false },
    critical:  { Critical: true, High: true, Important: true,          Minor: true,  Info: false },
  },
  final_review: {
    any:       { Critical: true, High: true, Important: true,          Minor: false, Info: false },
  },
}

function isIssueBlocking(reviewStage, taskRisk, severity, explicitFlag) {
  if (explicitFlag === true) return true
  if (explicitFlag === false) return false
  const key = reviewStage === 'final_review' ? 'any' : taskRisk
  const table = REVIEW_THRESHOLD[reviewStage]
  if (!table || !table[key]) return severity === 'Critical' || severity === 'High'
  const rule = table[key][severity]
  if (rule === true) return true
  if (rule === false) return false
  return explicitFlag === true
}

// ── Blocker classification ────────────────────────────────────────────

function classifyBlocker(detail) {
  if (!detail) return 'agent_output_invalid'
  const lower = detail.toLowerCase()
  if (lower.includes('merge conflict') || lower.includes('conflict')) return 'merge_conflict'
  if (lower.includes('permission') || lower.includes('access denied') || lower.includes('forbidden')) return 'permissions'
  if (lower.includes('external') || lower.includes('service') || lower.includes('timeout') || lower.includes('network')) return 'external_service'
  if (lower.includes('tool') || lower.includes('command not found') || lower.includes('not installed')) return 'tooling_unavailable'
  if (lower.includes('test') && (lower.includes('fail') || lower.includes('error'))) return 'test_failure'
  if (lower.includes('runtime') || lower.includes('crash') || lower.includes('exception')) return 'runtime_failure'
  if (lower.includes('depend') || lower.includes('import') || lower.includes('module')) return 'dependency_failure'
  if (lower.includes('architect') || lower.includes('design decision')) return 'architecture_decision'
  if (lower.includes('scope') || lower.includes('too large') || lower.includes('too complex')) return 'scope_too_large'
  if (lower.includes('context') || lower.includes('missing info') || lower.includes('unclear')) return 'missing_context'
  return 'agent_output_invalid'
}

// ── Escalation ladder executor ────────────────────────────────────────

async function runEscalationLadder(task, impl, classifyReason) {
  let currentImpl = impl
  let currentReason = classifyReason
  const attempts = []

  for (const rung of ESCALATION_LADDER) {
    const maxAttempts = ESCALATION_ATTEMPTS[rung]
    for (let attempt = 0; attempt < maxAttempts; attempt++) {
      log(task.id + ': escalation ' + rung + ' attempt ' + (attempt + 1) + '/' + maxAttempts)

      let result = null
      if (rung === 'schema_retry') {
        result = await agent(implementPrompt(task),
          opts('escalate-schema-retry:' + task.id, 'Implement', IMPLEMENT_RESULT))
      } else if (rung === 'self_service_retry') {
        result = await agent(selfServicePrompt(task),
          opts('escalate-self-service:' + task.id, 'Implement', IMPLEMENT_RESULT))
      } else if (rung === 'ask_user') {
        log(task.id + ': BLOCKED — escalation exhausted, asking user: ' + currentReason)
        attempts.push({ rung, attempt: attempt + 1, result: null })
        return { impl: currentImpl, reason: currentReason, classification: classifyBlocker(currentReason), rung_reached: rung, attempts, escalated_to_user: true }
      } else {
        // stronger_model, split_subtask, enriched_context — log and continue
        log(task.id + ': escalation rung ' + rung + ' — no automated action, escalating')
        continue
      }

      if (result && result.status !== 'BLOCKED') {
        log(task.id + ': escalation ' + rung + ' succeeded')
        return { impl: result, reason: null, classification: null, rung_reached: rung, attempts, escalated_to_user: false }
      }

      if (result && result.status === 'BLOCKED') {
        currentReason = result.blocker_detail || currentReason
      }

      attempts.push({ rung, attempt: attempt + 1, result })
    }
  }

  return { impl: currentImpl, reason: currentReason, classification: classifyBlocker(currentReason), rung_reached: 'ask_user', attempts, escalated_to_user: true }
}

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
    verification_commands: { type: 'array', items: { type: 'string' }, description: 'Commands to verify the implementation' },
    evidence_paths: { type: 'array', items: { type: 'string' }, description: 'Paths to evidence artifacts' },
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
          severity: { type: 'string', enum: ['Critical', 'High', 'Important', 'Minor', 'Info'] },
          file: { type: 'string' },
          line: { type: 'number' },
          description: { type: 'string' },
          blocking: { type: 'boolean' },
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

// ── Schema retry helper ───────────────────────────────────────────────

async function agentWithSchemaRetry(prompt, agentOpts, maxSchemaRetries) {
  const retries = maxSchemaRetries != null ? maxSchemaRetries : 1
  let result = await agent(prompt, agentOpts)
  if (result) return result
  for (let i = 0; i < retries; i++) {
    log(agentOpts.label + ': schema retry ' + (i + 1) + '/' + retries + ' (agent returned invalid result)')
    result = await agent(prompt, agentOpts)
    if (result) return result
  }
  return null
}

// ── Helper: check if review issues have blocking ones per threshold table ──

function hasBlockingIssues(review, reviewStage, taskRisk) {
  if (!review || !review.issues) return false
  return review.issues.some(issue => {
    const sev = issue.severity || 'Info'
    return isIssueBlocking(reviewStage, taskRisk, sev, issue.blocking)
  })
}

// ── Extract evidence from impl result ─────────────────────────────────

function extractEvidence(task, impl, specReview, codeReview) {
  return {
    commit_sha: (impl && impl.commit_sha) || '',
    test_results: (impl && impl.test_results) || '',
    verification_commands: (impl && impl.verification_commands) || (task.verification) || [],
    evidence_paths: (impl && impl.evidence_paths) || [],
    concerns: (impl && impl.concerns) || [],
    files_modified: (impl && impl.files_modified) || [],
  }
}

// ── Result adapter: classify task into exactly one partition ──────────

function classifyTaskResult(taskId, task, ctx) {
  // 1. Blocked at implementation
  if (ctx._blocked) {
    const classification = classifyBlocker(ctx._reason)
    return {
      partition: 'blocked',
      entry: {
        id: taskId,
        reason: ctx._reason,
        classification,
        impl: ctx.impl,
      },
    }
  }

  // 2. Escalated to user after ladder exhausted
  if (ctx._escalated_to_user) {
    return {
      partition: 'needs_escalation',
      entry: {
        id: taskId,
        reason: ctx._escalation_reason,
        classification: ctx._escalation_classification,
        rung_reached: ctx._escalation_rung,
        impl: ctx.impl,
      },
    }
  }

  // 3. Spec review cap exhausted with blocking issues
  if (!ctx.spec_passed && ctx._spec_review_exhausted) {
    return {
      partition: 'failed_review',
      entry: {
        id: taskId,
        stage: 'spec_review',
        blocking_issues: (ctx.spec_review && ctx.spec_review.issues) || [],
        iterations: ctx._iterations_spec || 0,
        evidence: extractEvidence(task, ctx.impl, ctx.spec_review, null),
      },
    }
  }

  // 4. Code review cap exhausted with blocking issues
  if (ctx.spec_passed && !ctx.code_passed && ctx._code_review_exhausted) {
    return {
      partition: 'failed_review',
      entry: {
        id: taskId,
        stage: 'code_review',
        blocking_issues: (ctx.code_review && ctx.code_review.issues) || [],
        iterations: ctx._iterations_code || 0,
        evidence: extractEvidence(task, ctx.impl, ctx.spec_review, ctx.code_review),
      },
    }
  }

  // 5. Spec or code review stalled (cap exhausted without precise blocking)
  if (!ctx.spec_passed || !ctx.code_passed) {
    return {
      partition: 'stalled',
      entry: {
        id: taskId,
        spec_passed: ctx.spec_passed || false,
        code_passed: ctx.code_passed || false,
        spec_iterations: ctx._iterations_spec || 0,
        code_iterations: ctx._iterations_code || 0,
        evidence: extractEvidence(task, ctx.impl, ctx.spec_review, ctx.code_review),
      },
    }
  }

  // 6. Passed: status DONE or DONE_WITH_CONCERNS, spec_passed, code_passed
  return {
    partition: 'passed',
    entry: {
      id: taskId,
      status: (ctx.impl && ctx.impl.status) || 'DONE',
      spec_passed: true,
      code_passed: true,
      spec_review: ctx.spec_review,
      code_review: ctx.code_review,
      evidence: extractEvidence(task, ctx.impl, ctx.spec_review, ctx.code_review),
      files: (ctx.impl && ctx.impl.files_modified) || [],
    },
  }
}

// ── Main execution ───────────────────────────────────────────────────

const partitions = {
  passed: [],
  completed: [],
  blocked: [],
  stalled: [],
  failed_review: [],
  needs_escalation: [],
}

const totalTasks = Object.keys(tasks).length
const taskRisk = 'medium' // default risk; per-task risk from task metadata

for (const [gi, group] of groups.entries()) {
  if (group.length === 0) continue
  log('Group ' + (gi + 1) + '/' + groups.length + ': ' + group.length + ' task(s)')

  const groupResults = await parallel(
    group.map(taskId => () => {
      const task = tasks[taskId]
      const risk = task.risk || taskRisk

      return pipeline(
        [task],

        // Stage 1: Implement (with schema retry)
        async (t) => {
          let result = await agentWithSchemaRetry(
            implementPrompt(t),
            opts('implement:' + t.id, 'Implement', IMPLEMENT_RESULT),
            ESCALATION_ATTEMPTS.schema_retry,
          )

          if (result && result.status === 'BLOCKED') {
            // Run escalation ladder for blocked tasks
            const escalation = await runEscalationLadder(t, result, result.blocker_detail)
            if (!escalation.escalated_to_user && escalation.impl && escalation.impl.status !== 'BLOCKED') {
              result = escalation.impl
            } else {
              if (escalation.escalated_to_user) {
                return {
                  ...t, impl: escalation.impl,
                  _blocked: true,
                  _reason: escalation.reason,
                  _escalated_to_user: true,
                  _escalation_reason: escalation.reason,
                  _escalation_classification: escalation.classification,
                  _escalation_rung: escalation.rung_reached,
                }
              }
            }
          }

          if (!result) {
            // Schema retry exhausted — agent returned null/invalid
            return {
              ...t, impl: null,
              _blocked: true,
              _reason: 'Agent returned invalid output after schema retry',
              _escalated_to_user: true,
              _escalation_reason: 'Agent returned invalid output after schema retry',
              _escalation_classification: 'agent_output_invalid',
              _escalation_rung: 'schema_retry',
            }
          }

          return { ...t, impl: result }
        },

        // Stage 2: Spec Review (with review threshold enforcement)
        async (ctx) => {
          const { impl, id } = ctx
          if (!impl || impl.status === 'BLOCKED') {
            return { ...ctx, spec_review: null, spec_passed: false, _blocked: true, _reason: (impl && impl.blocker_detail) || 'BLOCKED' }
          }

          let review = await agentWithSchemaRetry(
            specReviewPrompt(ctx, impl),
            opts('spec-review:' + id, 'Spec Review', REVIEW_RESULT),
            0,
          )

          let iterations = 0
          const hasBlocking = () => hasBlockingIssues(review, 'spec_review', risk)

          while (review && hasBlocking() && iterations < MAX_RETRIES) {
            const blockingIssues = review.issues.filter(i =>
              isIssueBlocking('spec_review', risk, i.severity, i.blocking)
            )
            log(id + ': spec review found ' + blockingIssues.length + ' blocking issue(s) — fixing')
            const updated = await agentWithSchemaRetry(
              fixPrompt(blockingIssues, impl.files_modified),
              opts('fix-spec:' + id, 'Spec Review', IMPLEMENT_RESULT),
              0,
            )
            if (updated) ctx.impl = { ...ctx.impl, ...updated }

            review = await agentWithSchemaRetry(
              specReviewPrompt(ctx, ctx.impl),
              opts('spec-review:' + id + '-r' + (iterations + 1), 'Spec Review', REVIEW_RESULT),
              0,
            )
            iterations++
          }

          const specPassed = review ? !hasBlocking() : false
          const exhausted = iterations >= MAX_RETRIES && !specPassed

          return {
            ...ctx,
            spec_review: review,
            spec_passed: specPassed,
            _iterations_spec: iterations,
            _spec_review_exhausted: exhausted,
          }
        },

        // Stage 3: Code Quality Review (with review threshold enforcement)
        async (ctx) => {
          if (ctx._blocked) return ctx
          if (!ctx.spec_passed) {
            // Spec didn't pass — mark review exhausted if applicable
            return {
              ...ctx,
              code_review: null,
              code_passed: false,
              _iterations_code: 0,
              _code_review_exhausted: ctx._spec_review_exhausted || false,
            }
          }

          let review = await agentWithSchemaRetry(
            codeReviewPrompt(ctx.impl, ctx.id),
            opts('code-review:' + ctx.id, 'Code Review', REVIEW_RESULT),
            0,
          )

          let iterations = 0
          const hasBlocking = () => hasBlockingIssues(review, 'code_review', risk)

          while (review && hasBlocking() && iterations < MAX_RETRIES) {
            const blockingIssues = review.issues.filter(i =>
              isIssueBlocking('code_review', risk, i.severity, i.blocking)
            )
            log(ctx.id + ': code review found ' + blockingIssues.length + ' blocking issue(s) — fixing')
            const updated = await agentWithSchemaRetry(
              fixPrompt(blockingIssues, ctx.impl.files_modified),
              opts('fix-code:' + ctx.id, 'Code Review', IMPLEMENT_RESULT),
              0,
            )
            if (updated) ctx.impl = { ...ctx.impl, ...updated }

            review = await agentWithSchemaRetry(
              codeReviewPrompt(ctx.impl, ctx.id),
              opts('code-review:' + ctx.id + '-r' + (iterations + 1), 'Code Review', REVIEW_RESULT),
              0,
            )
            iterations++
          }

          const codePassed = review ? !hasBlocking() : false
          const exhausted = iterations >= MAX_RETRIES && !codePassed

          return {
            ...ctx,
            code_review: review,
            code_passed: codePassed,
            _iterations_code: iterations,
            _code_review_exhausted: exhausted,
          }
        },
      )
    }),
  )

  // Classify each task into exactly one partition
  for (const r of groupResults.flat().filter(Boolean)) {
    const taskId = r.id
    const task = tasks[taskId]
    const { partition, entry } = classifyTaskResult(taskId, task, r)
    partitions[partition].push(entry)
  }
}

// ── Enforce invariant: completed == passed ────────────────────────────

for (const entry of partitions.passed) {
  partitions.completed.push({ ...entry })
}

// ── Guard: Final Review only when ALL tasks passed ────────────────────
// Runs only when completed.length == totalTasks AND all other partitions empty

const allOtherPartitionsEmpty =
  partitions.blocked.length === 0 &&
  partitions.stalled.length === 0 &&
  partitions.failed_review.length === 0 &&
  partitions.needs_escalation.length === 0

let finalReview = null
if (partitions.completed.length === totalTasks && allOtherPartitionsEmpty && totalTasks > 0) {
  phase('Final Review')
  const allFiles = partitions.completed.flatMap(r => r.files || r.evidence?.files_modified || []).filter(Boolean)
  const allIds = partitions.completed.map(r => r.id).join(', ')

  finalReview = await agent(
    codeReviewPrompt(
      { summary: 'Entire implementation: ' + allIds, files_modified: allFiles },
      'final',
    ),
    opts('final-review', 'Final Review', REVIEW_RESULT),
  )
}

// ── Build state_patch for resume support ──────────────────────────────

const state_patch = {
  partitions: {
    passed: partitions.passed.map(e => e.id),
    completed: partitions.completed.map(e => e.id),
    blocked: partitions.blocked.map(e => e.id),
    stalled: partitions.stalled.map(e => e.id),
    failed_review: partitions.failed_review.map(e => e.id),
    needs_escalation: partitions.needs_escalation.map(e => e.id),
  },
  total_tasks: totalTasks,
  final_review_run: finalReview !== null,
}

return {
  passed: partitions.passed,
  completed: partitions.completed,
  blocked: partitions.blocked,
  stalled: partitions.stalled,
  failed_review: partitions.failed_review,
  needs_escalation: partitions.needs_escalation,
  final_review: finalReview,
  state_patch,
}
