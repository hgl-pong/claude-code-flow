export const meta = {
  name: 'execute-plan',
  description:
    'Execute implementation plan tasks — implement, spec review, code quality review — with dependency-aware pipeline orchestration',
  phases: [
    { title: 'Implement', detail: 'Implement tasks in parallel' },
    { title: 'Spec Review', detail: 'Verify each task matches its requirements' },
    { title: 'Code Review', detail: 'Review code quality for each task' },
    { title: 'Final Review', detail: 'Cross-task code review' },
  ],
}

const { groups, tasks, prompts, worktree, model_tasks } = args
const MAX_RETRIES = 5

// ── Schemas ──────────────────────────────────────────────────────────

const IMPLEMENT_RESULT = {
  type: 'object',
  additionalProperties: false,
  properties: {
    status: {
      type: 'string',
      enum: ['DONE', 'DONE_WITH_CONCERNS', 'BLOCKED'],
    },
    summary: { type: 'string', description: 'What was implemented and how' },
    files_modified: {
      type: 'array',
      items: { type: 'string' },
      description: 'Every file created or changed',
    },
    test_results: { type: 'string', description: 'Test command and output' },
    commit_sha: { type: 'string', description: 'Git commit SHA (short)' },
    concerns: {
      type: 'array',
      items: { type: 'string' },
      description: 'If DONE_WITH_CONCERNS, list each concern',
    },
    blocker_detail: {
      type: 'string',
      description: 'If BLOCKED: what blocks you, what you tried',
    },
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
          severity: {
            type: 'string',
            enum: ['Critical', 'Important', 'Minor'],
          },
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

// ── Helpers ──────────────────────────────────────────────────────────

function fill(template, vars) {
  let s = template
  for (const [k, v] of Object.entries(vars)) {
    s = s.replaceAll('{{' + k + '}}', String(v))
  }
  return s
}

function agentOpts(label, phase, schema) {
  const opts = { label, phase, schema }
  if (model_tasks) opts.model = model_tasks
  return opts
}

// ── Prompt builders ──────────────────────────────────────────────────

function implPrompt(task) {
  return fill(prompts.implement, {
    TASK_ID: task.id,
    TASK_DESCRIPTION: task.description,
    WORKTREE: worktree,
  })
}

function specReviewPrompt(ctx) {
  return fill(prompts.specReview, {
    TASK_DESCRIPTION: ctx.description,
    IMPLEMENTER_SUMMARY: ctx.impl.summary,
    FILES_MODIFIED: ctx.impl.files_modified.join(', '),
  })
}

function codeReviewPrompt(ctx) {
  return fill(prompts.codeReview, {
    TASK_SUMMARY: ctx.impl.summary,
    COMMIT_SHA: ctx.impl.commit_sha || 'HEAD',
    FILES_MODIFIED: ctx.impl.files_modified.join(', '),
  })
}

function fixPrompt(issues, files) {
  return fill(prompts.fix, {
    ISSUES: JSON.stringify(issues, null, 2),
    FILES_MODIFIED: files.join(', '),
  })
}

// ── Main ─────────────────────────────────────────────────────────────

const results = { completed: [], blocked: [] }

for (const [gi, group] of groups.entries()) {
  if (group.length === 0) continue
  log(`Group ${gi + 1}/${groups.length}: ${group.length} task(s)`)

  const groupResults = await parallel(
    group.map(taskId => () => {
      const task = tasks[taskId]

      return pipeline(
        [task],

        // ─── Stage 1: Implement ──────────────────────────────
        async (t) => {
          phase('Implement')
          let result = await agent(implPrompt(t),
            agentOpts(`implement:${t.id}`, 'Implement', IMPLEMENT_RESULT))

          // Self-service retry if agent hit a dead end
          if (result.status === 'BLOCKED') {
            log(`${t.id}: BLOCKED — retrying with self-service prompt`)
            result = await agent(
              implPrompt(t) +
                '\n\n## Escalation Rejected\n\n' +
                'You reported BLOCKED. Re-examine: can you solve this by ' +
                'searching the codebase more thoroughly, picking a simpler ' +
                'approach, or narrowing scope? ' +
                'Only report BLOCKED again if truly impossible.',
              agentOpts(`implement:${t.id}-r2`, 'Implement', IMPLEMENT_RESULT))
          }

          return { ...t, impl: result }
        },

        // ─── Stage 2: Spec Review ────────────────────────────
        async (ctx) => {
          const { impl, id } = ctx
          if (impl.status === 'BLOCKED') {
            return {
              ...ctx,
              spec_review: null,
              _blocked: true,
              _reason: impl.blocker_detail || 'BLOCKED',
            }
          }

          phase('Spec Review')
          let review = await agent(specReviewPrompt(ctx),
            agentOpts(`spec-review:${id}`, 'Spec Review', REVIEW_RESULT))

          let iterations = 0
          while (!review.passed && iterations < MAX_RETRIES) {
            log(`${id}: spec review found ${review.issues.length} issue(s) — fixing`)
            const updated = await agent(
              fixPrompt(review.issues, impl.files_modified),
              agentOpts(`fix-spec:${id}`, 'Spec Review', IMPLEMENT_RESULT))
            ctx.impl = { ...ctx.impl, ...updated }

            review = await agent(specReviewPrompt(ctx),
              agentOpts(`spec-review:${id}-r${iterations + 1}`, 'Spec Review', REVIEW_RESULT))
            iterations++
          }

          return {
            ...ctx,
            spec_review: review,
            spec_passed: review.passed,
            _iterations_spec: iterations,
          }
        },

        // ─── Stage 3: Code Quality Review ─────────────────────
        async (ctx) => {
          if (ctx._blocked || !ctx.spec_passed) return ctx

          phase('Code Review')
          let review = await agent(codeReviewPrompt(ctx),
            agentOpts(`code-review:${ctx.id}`, 'Code Review', REVIEW_RESULT))

          let iterations = 0
          while (
            review.issues.some(i => i.severity === 'Critical') &&
            iterations < MAX_RETRIES
          ) {
            const criticals = review.issues.filter(i => i.severity === 'Critical')
            log(`${ctx.id}: code review found ${criticals.length} critical issue(s) — fixing`)
            const updated = await agent(
              fixPrompt(criticals, ctx.impl.files_modified),
              agentOpts(`fix-code:${ctx.id}`, 'Code Review', IMPLEMENT_RESULT))
            ctx.impl = { ...ctx.impl, ...updated }

            review = await agent(codeReviewPrompt(ctx),
              agentOpts(`code-review:${ctx.id}-r${iterations + 1}`, 'Code Review', REVIEW_RESULT))
            iterations++
          }

          return {
            ...ctx,
            code_review: review,
            code_passed: !review.issues.some(i => i.severity === 'Critical'),
            _iterations_code: iterations,
          }
        },
      )
    }),
  )

  // Collect per-task results
  for (const taskResult of groupResults.flat().filter(Boolean)) {
    if (taskResult._blocked) {
      results.blocked.push({
        id: taskResult.id,
        reason: taskResult._reason,
        impl: taskResult.impl,
      })
    } else {
      results.completed.push({
        id: taskResult.id,
        spec_passed: taskResult.spec_passed,
        code_passed: taskResult.code_passed,
        code_review: taskResult.code_review,
        files: taskResult.impl.files_modified,
      })
    }
  }
}

// ── Final cross-task code review ─────────────────────────────────────

const allPassed =
  results.completed.length > 0 &&
  results.completed.every(r => r.code_passed)

if (allPassed) {
  phase('Final Review')
  const filesSummary = results.completed
    .flatMap(r => r.files)
    .filter(Boolean)
    .join(', ')

  const finalReview = await agent(
    fill(prompts.codeReview, {
      TASK_SUMMARY:
        'Entire implementation: ' +
        results.completed.map(r => r.id).join(', '),
      COMMIT_SHA: 'HEAD',
      FILES_MODIFIED: filesSummary,
    }),
    agentOpts('final-review', 'Final Review', REVIEW_RESULT),
  )
  results.final_review = finalReview
}

return results
