// Invoked by the workflow-driven-development skill for the full-auto pipeline mode.
// Orchestrates: scope → research → synthesize spec → review spec → write plan →
// review plan → parse plan → execute (delegates to execute-plan workflow) → 7 gates.
//
// See SKILL.md for launch instructions.
// Delegates to execute-plan.workflow.js via workflow() at the Execute phase.

export const meta = {
  name: 'full-auto-pipeline',
  description:
    'Full auto-mode pipeline: research → spec → plan review → parse plan → execute → gates',
  phases: [
    { title: 'Scope', detail: 'Determine research angles' },
    { title: 'Research', detail: 'Parallel research per angle' },
    { title: 'Synthesize Spec', detail: 'Write .claude/specs/' },
    { title: 'Review Spec', detail: 'Adversarial spec review' },
    { title: 'Write Plan', detail: 'Decompose spec into tasks' },
    { title: 'Review Plan', detail: 'Verify plan completeness' },
    { title: 'Parse Plan', detail: 'Extract structured tasks from plan' },
    { title: 'Execute', detail: 'Implement → spec review → code review' },
    { title: 'Gates', detail: '7 completion gates' },
  ],
}

const {
  task,
  worktree,
  specs_dir,
  plans_dir,
  execute_plan_script_path,
  model_tasks,
  max_retries,
} = args

const RETRIES = max_retries || 5
const GATE_RETRIES = 10

// ── Contract constants ────────────────────────────────────────────────

const PHASE_ORDER = [
  'scope', 'research', 'synthesize_spec', 'review_spec',
  'write_plan', 'review_plan', 'parse_plan', 'execute', 'gates', 'finalize',
]

const EXECUTE_SUBFLOW_STAGES = ['Implement', 'Spec Review', 'Code Review']

const CANONICAL_GATES = [
  'tasks_executed',
  'reviews_passed',
  'tests_pass',
  'runtime_evidence',
  'spec_verified',
  'final_review',
  'git_clean',
]

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

const REVIEW_RETRY_CAP_DEFAULT = 5
const GATE_RETRY_CAP_DEFAULT = 10

const TASK_METADATA_DEFAULTS = {
  risk: 'medium',
  subsystem: 'unknown',
  runtime_evidence_required: 'optional',
  depends_on: [],
  files: [],
  tests: [],
  verification: [],
  acceptance_refs: [],
  concerns: [],
}

const TASK_STATUSES = [
  'queued', 'implementing', 'implemented', 'spec_reviewing', 'code_reviewing',
  'passed', 'blocked', 'stalled', 'failed_review', 'failed', 'split',
]

const TERMINAL_STATUSES = ['DONE', 'STOPPED_ASK_USER', 'FAILED_FATAL', 'CANCELLED']
const NONTERMINAL_STATUSES = ['ACTIVE', 'PAUSED_COMPACTING', 'BLOCKED_ESCALATING']

// Review threshold table: [review_stage][task_risk] -> which severities block
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
  // 'if_explicit' — blocking only if issue explicitly marked blocking=true
  return explicitFlag === true
}

function validateGateSet(gateStates) {
  const reported = Object.keys(gateStates)
  const canonical = CANONICAL_GATES.map(g => 'gate_' + (CANONICAL_GATES.indexOf(g) + 1) + '_' + g)
  const missing = canonical.filter(g => !reported.includes(g))
  return { valid: missing.length === 0, missing }
}

function agentOpts(label, phase, schema) {
  const opts = { label, phase, schema }
  if (model_tasks) opts.model = model_tasks
  return opts
}

// ── Schemas ──────────────────────────────────────────────────────────

const ANGLES_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    strategy: { type: 'string' },
    angles: {
      type: 'array', minItems: 3, maxItems: 6,
      items: {
        type: 'object', additionalProperties: false,
        properties: {
          key: { type: 'string' },
          question: { type: 'string' },
        },
        required: ['key', 'question'],
      },
    },
  },
  required: ['strategy', 'angles'],
}

const RESEARCH_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    angle: { type: 'string' },
    findings: { type: 'string' },
    key_insights: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['angle', 'findings', 'key_insights'],
}

const SPEC_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    spec_path: { type: 'string' },
    summary: { type: 'string' },
  },
  required: ['spec_path', 'summary'],
}

const REVIEW_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    passed: { type: 'boolean' },
    issues: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          severity: { type: 'string', enum: ['Critical', 'Important', 'Minor'] },
          description: { type: 'string' },
        },
        required: ['severity', 'description'],
      },
    },
    summary: { type: 'string' },
  },
  required: ['passed', 'issues', 'summary'],
}

const PLAN_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    plan_path: { type: 'string' },
    task_count: { type: 'number' },
    dependency_groups: { type: 'number' },
    summary: { type: 'string' },
  },
  required: ['plan_path', 'task_count', 'dependency_groups'],
}

// Structured task extraction — used by parse-plan agent
const TASK_ITEM_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    id: { type: 'string', pattern: '^task-' },
    description: { type: 'string', minLength: 1 },
    depends_on: { type: 'array', items: { type: 'string' } },
    files: { type: 'array', items: { type: 'string' } },
    tests: { type: 'array', items: { type: 'string' } },
    verification: { type: 'array', items: { type: 'string' } },
    acceptance_refs: { type: 'array', items: { type: 'string' } },
    runtime_evidence_required: {
      type: 'string',
      enum: ['required', 'optional', 'not_needed'],
    },
    risk: { type: 'string', enum: TASK_RISKS },
    subsystem: { type: 'string' },
  },
  required: ['id', 'description'],
}

const TASKS_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    groups: {
      type: 'array', items: {
        type: 'array', items: { type: 'string' },
        description: 'Array of task ID arrays, one per topological level',
      },
    },
    tasks: {
      type: 'object',
      additionalProperties: false,
      propertyNames: { pattern: '^task-' },
      properties: {}, // per-task shape defined by TASK_ITEM_SCHEMA, enforced in validation
      description: 'Object keyed by task ID, each with rich metadata',
    },
  },
  required: ['groups', 'tasks'],
}

// ── Plan validation ───────────────────────────────────────────────────

const REQUIRED_METADATA_FOR_RISK = ['high', 'critical']
const REQUIRED_FIELDS_FOR_RISK = ['files', 'tests', 'verification']
const REQUIRED_FIELDS_FOR_RUNTIME = ['verification', 'acceptance_refs']

function validateParsedPlan(parsed) {
  const errors = []
  const { groups, tasks } = parsed
  const allIds = Object.keys(tasks)
  const idSet = new Set(allIds)

  // 1. Check for duplicate IDs (within tasks object keys)
  const seenIds = new Set()
  for (const tid of allIds) {
    if (seenIds.has(tid)) {
      errors.push({ code: 'duplicate_id', task: tid, detail: `Duplicate task ID: ${tid}` })
    }
    seenIds.add(tid)
    // Also check id field matches key
    const task = tasks[tid]
    if (task.id && task.id !== tid) {
      errors.push({ code: 'id_mismatch', task: tid, detail: `Task key ${tid} has id field ${task.id}` })
    }
  }

  // 2. Empty descriptions
  for (const tid of allIds) {
    const desc = tasks[tid].description
    if (!desc || desc.trim().length === 0) {
      errors.push({ code: 'empty_description', task: tid, detail: `Task ${tid} has empty description` })
    }
  }

  // 3. Unknown deps
  for (const tid of allIds) {
    const deps = tasks[tid].depends_on || []
    for (const dep of deps) {
      if (!idSet.has(dep)) {
        errors.push({ code: 'unknown_dep', task: tid, detail: `Task ${tid} depends on unknown task ${dep}` })
      }
    }
  }

  // 4. Cycle detection via DFS
  const WHITE = 0, GRAY = 1, BLACK = 2
  const color = Object.fromEntries(allIds.map(id => [id, WHITE]))
  function dfs(node) {
    color[node] = GRAY
    for (const dep of (tasks[node].depends_on || [])) {
      if (!idSet.has(dep)) continue // unknown dep already reported
      if (color[dep] === GRAY) {
        errors.push({ code: 'cycle', detail: `Dependency cycle involving ${node} and ${dep}` })
        return
      }
      if (color[dep] === WHITE) dfs(dep)
    }
    color[node] = BLACK
  }
  for (const tid of allIds) {
    if (color[tid] === WHITE) dfs(tid)
  }

  // 5. Empty groups
  for (let i = 0; i < groups.length; i++) {
    if (groups[i].length === 0) {
      errors.push({ code: 'empty_group', detail: `Group ${i} is empty` })
    }
  }

  // 6. Skipped groups (empty group between non-empty groups)
  let firstNonEmpty = -1, lastNonEmpty = -1
  for (let i = 0; i < groups.length; i++) {
    if (groups[i].length > 0) {
      if (firstNonEmpty === -1) firstNonEmpty = i
      lastNonEmpty = i
    }
  }
  for (let i = firstNonEmpty; i <= lastNonEmpty; i++) {
    if (groups[i].length === 0) {
      errors.push({ code: 'skipped_group', detail: `Group ${i} is empty between non-empty groups` })
    }
  }

  // 7. Duplicate group membership
  const groupMembership = new Map()
  for (let i = 0; i < groups.length; i++) {
    for (const tid of groups[i]) {
      if (groupMembership.has(tid)) {
        errors.push({ code: 'duplicate_group_membership', task: tid,
          detail: `Task ${tid} appears in groups ${groupMembership.get(tid)} and ${i}` })
      }
      groupMembership.set(tid, i)
    }
  }

  // 8. Tasks not in any group
  const grouped = new Set(groups.flat())
  for (const tid of allIds) {
    if (!grouped.has(tid)) {
      errors.push({ code: 'ungrouped_task', task: tid, detail: `Task ${tid} not in any group` })
    }
  }

  // 9. Group IDs not in tasks
  for (const tid of grouped) {
    if (!idSet.has(tid)) {
      errors.push({ code: 'unknown_group_task', detail: `Group references unknown task ${tid}` })
    }
  }

  // 10. Intra-group dependencies
  for (let i = 0; i < groups.length; i++) {
    const groupSet = new Set(groups[i])
    for (const tid of groups[i]) {
      for (const dep of (tasks[tid].depends_on || [])) {
        if (groupSet.has(dep)) {
          errors.push({ code: 'intra_group_dep', task: tid, detail:
            `Task ${tid} depends on ${dep} within same group ${i}` })
        }
      }
    }
  }

  // 11. Forward dependencies (task depends on a task in a later group)
  const taskGroup = new Map()
  for (let i = 0; i < groups.length; i++) {
    for (const tid of groups[i]) taskGroup.set(tid, i)
  }
  for (const tid of allIds) {
    for (const dep of (tasks[tid].depends_on || [])) {
      if (!taskGroup.has(dep) || !taskGroup.has(tid)) continue
      if (taskGroup.get(dep) > taskGroup.get(tid)) {
        errors.push({ code: 'forward_dep', task: tid, detail:
          `Task ${tid} (group ${taskGroup.get(tid)}) depends on ${dep} (group ${taskGroup.get(dep)})` })
      }
    }
  }

  // 12. Required metadata for high/critical risk tasks
  for (const tid of allIds) {
    const risk = tasks[tid].risk || TASK_METADATA_DEFAULTS.risk
    if (REQUIRED_METADATA_FOR_RISK.includes(risk)) {
      for (const field of REQUIRED_FIELDS_FOR_RISK) {
        const val = tasks[tid][field]
        if (!val || (Array.isArray(val) && val.length === 0)) {
          errors.push({ code: 'missing_required_metadata', task: tid, detail:
            `Task ${tid} (risk=${risk}) missing required field: ${field}` })
        }
      }
    }
  }

  // 13. Required metadata for runtime_evidence_required tasks
  for (const tid of allIds) {
    const rte = tasks[tid].runtime_evidence_required || TASK_METADATA_DEFAULTS.runtime_evidence_required
    if (rte === 'required') {
      for (const field of REQUIRED_FIELDS_FOR_RUNTIME) {
        const val = tasks[tid][field]
        if (!val || (Array.isArray(val) && val.length === 0)) {
          errors.push({ code: 'missing_runtime_metadata', task: tid, detail:
            `Task ${tid} (runtime_evidence_required) missing field: ${field}` })
        }
      }
    }
  }

  return { valid: errors.length === 0, errors }
}

const GATE_RESULT = {
  type: 'object', additionalProperties: false,
  properties: {
    gate: { type: 'number' },
    passed: { type: 'boolean' },
    detail: { type: 'string' },
    fix_applied: { type: 'string' },
  },
  required: ['gate', 'passed', 'detail'],
}

// ── Helper: spec file name ───────────────────────────────────────────

const specId = task
  .replace(/[^a-z0-9]+/gi, '-')
  .replace(/^-+|-+$/g, '')
  .toLowerCase()
  .slice(0, 60)
const specPath = `${specs_dir}/${specId}.md`
const planPath = `${plans_dir}/${specId}-plan.md`

// ── Phase 1: Scope ───────────────────────────────────────────────────

phase('Scope')
const scope = await agent(
  `Explore the codebase to understand existing architecture, then define research
angles for this task.

## Task

${task}

## Worktree

${worktree}

## Instructions

1. Explore the codebase: architecture, conventions, dependencies, file structure
2. Define a one-paragraph strategy for how to approach this task
3. Define 3-6 research angles. Each angle investigates a distinct concern:

- Prior art / similar solutions in this codebase
- Technical architecture and constraints
- User-facing behavior and interface patterns
- Data flow, state management, API contracts
- Edge cases, error handling, failure modes
- Testing strategy and verification approach

Make angles specific to this task and codebase. The goal is that after
researching all angles, we have enough information to write a complete,
implementable spec.`,
  agentOpts('scope', 'Scope', ANGLES_SCHEMA),
)

log(`Strategy: ${scope.strategy}`)
log(`Angles: ${scope.angles.map(a => a.key).join(', ')}`)

// ── Phase 2: Research ────────────────────────────────────────────────

phase('Research')
const researchResults = await parallel(
  scope.angles.map(angle => () =>
    agent(
      `Research this angle for the task. Search the codebase (and web if needed).

## Task

${task}

## Strategy

${scope.strategy}

## Your Angle: ${angle.key}

${angle.question}

Produce detailed findings with file paths, line numbers, or URLs.
3-5 key insights. Note open questions. Be thorough — your findings
feed directly into the specification.`,
      agentOpts(`research:${angle.key}`, 'Research', RESEARCH_SCHEMA),
    ),
  ),
)

const allFindings = researchResults.filter(Boolean)
log(`Research done: ${allFindings.length}/${scope.angles.length} angles`)

// ── Phase 3: Synthesize Spec ─────────────────────────────────────────

phase('Synthesize Spec')
const researchText = allFindings.map(r =>
  `## ${r.angle}\n\n${r.findings}\n\nKey insights:\n${r.key_insights.map(i => `- ${i}`).join('\n')}`
).join('\n\n---\n\n')

const openQuestionsText = allFindings
  .flatMap(r => r.open_questions).filter(Boolean)
  .map(q => `- ${q}`).join('\n')

let spec = await agent(
  `Write a complete, implementable development spec based on this research.

## Task

${task}

## Research

${researchText}

## Open Questions — resolve with best-guess defaults

${openQuestionsText || 'None'}

## Instructions

1. Resolve open questions with reasonable defaults. Record your decisions.
2. Decision principles: YAGNI scope, existing codebase patterns first,
   simplest architecture, match project conventions
3. Write spec to: ${specPath}
4. Structure:

\`\`\`markdown
# Spec: ${task}

## Overview
(one paragraph — what, why, for whom)

## Requirements
(bullet list — each requirement is testable)

## Architecture
(what changes, what stays — components, files, data flow)

## UI/UX (if applicable)
(component hierarchy, states: loading/empty/error/edge, key interactions)

## Testing Strategy
(unit tests for X, integration tests for Y, smoke check for Z)

## Acceptance Criteria
(numbered, verifiable — "when user does X, system does Y")
\`\`\`

Use the Write tool to save the file. Return the path and summary.`,
  agentOpts('synthesize-spec', 'Synthesize Spec', SPEC_SCHEMA),
)

log(`Spec: ${spec.spec_path}`)

// ── Phase 4: Review Spec ─────────────────────────────────────────────

phase('Review Spec')
let specReview = await agent(
  `Adversarially review the spec. Read ${spec.spec_path} and find every gap.

Challenge every assumption. If the spec says "should support X", ask: is X
essential to "${task}"? Flag: missing requirements, over-engineering, ambiguity,
missing edge cases/error states, underspecified acceptance criteria.

Critical: not implementable as-is.
Important: significant gap or scope creep.
Minor: wording or clarity.`,
  agentOpts('review-spec', 'Review Spec', REVIEW_SCHEMA),
)

let specIterations = 0
while (!specReview.passed && specIterations < RETRIES) {
  log(`Spec issues: ${specReview.issues.length} — revising`)

  spec = await agent(
    `Revise the spec at ${spec.spec_path}. Only fix these issues — keep everything else:
${JSON.stringify(specReview.issues, null, 2)}

Read the file, apply fixes, write it back.`,
    agentOpts(`fix-spec-r${specIterations + 1}`, 'Review Spec', SPEC_SCHEMA),
  )

  specReview = await agent(
    `Re-review the spec at ${spec.spec_path}. Verify each of these is actually fixed:
${JSON.stringify(specReview.issues, null, 2)}

Read the file independently. Do not trust that they were fixed.`,
    agentOpts(`review-spec-r${specIterations + 1}`, 'Review Spec', REVIEW_SCHEMA),
  )
  specIterations++
}
log(`Spec review: ${specReview.passed ? 'PASSED' : `STALLED (${specIterations} iters)`}`)

// ── Phase 5: Write Plan ──────────────────────────────────────────────

phase('Write Plan')
const planResult = await agent(
  `Decompose the spec into an implementation plan. Write to ${planPath}.

1. Read the spec at ${spec.spec_path}
2. Break into atomic tasks. Each task: distinct files, clear description,
   implementation details, depends_on list, verification command
3. Rules: auto-split independent subsystems; each task completable in one session;
   every spec requirement covered by at least one task
4. Format each task as:

\`\`\`markdown
## Task N: [name]

**Depends on:** none  OR  **Depends on:** task-1, task-2

[description with implementation details]

**Files:** \`src/...\`

**Tests:** \`test/...\`

**Verification:** \`command\`
\`\`\`

Return the plan path, task count, and number of topological levels.`,
  agentOpts('write-plan', 'Write Plan', PLAN_SCHEMA),
)

log(`Plan: ${planResult.plan_path} (${planResult.task_count} tasks)`)

// ── Phase 6: Review Plan ─────────────────────────────────────────────

phase('Review Plan')
let planReview = await agent(
  `Review the plan at ${planResult.plan_path} against the spec at ${specPath}.

Verify: every spec requirement covered, dependencies correct (no cycles,
no missing), each task atomic and independently completable.

Critical: missing requirement, broken dependency.
Important: task too large, unclear scope.
Minor: wording.`,
  agentOpts('review-plan', 'Review Plan', REVIEW_SCHEMA),
)

let planIterations = 0
while (!planReview.passed && planIterations < RETRIES) {
  log(`Plan issues: ${planReview.issues.length} — revising`)
  await agent(
    `Fix the plan at ${planResult.plan_path}:
${JSON.stringify(planReview.issues, null, 2)}
Read plan and spec. Edit only what the issues describe.`,
    agentOpts(`fix-plan-r${planIterations + 1}`, 'Review Plan', { type: 'object' }),
  )
  planReview = await agent(
    `Re-review the plan. Verify these issues are fixed:
${JSON.stringify(planReview.issues, null, 2)}
Read the plan file independently.`,
    agentOpts(`review-plan-r${planIterations + 1}`, 'Review Plan', REVIEW_SCHEMA),
  )
  planIterations++
}
log(`Plan review: ${planReview.passed ? 'PASSED' : `STALLED (${planIterations} iters)`}`)

// ── Phase 7: Parse Plan — extract structured tasks ────────────────────

phase('Parse Plan')
const parsed = await agent(
  `Read the plan at ${planResult.plan_path} and extract its tasks into structured form.

You will return two things:
1. \`groups\`: array of task ID arrays, one per topological level.
   Level 0 = tasks with no dependencies.
   Level 1 = tasks that depend only on Level 0 tasks.
   Level N = tasks that depend only on earlier levels.
2. \`tasks\`: object keyed by task ID. Each task has rich metadata:

Required fields per task:
- id: "task-N"
- description: FULL task text from the plan (all details, must not be empty)

Extracted from plan where present, inferred otherwise:
- depends_on: array of task IDs this task depends on (empty if none)
- files: array of file paths the task touches
- tests: array of test file paths
- verification: array of verification commands
- acceptance_refs: array of acceptance criteria identifiers from the spec
- runtime_evidence_required: "required" | "optional" | "not_needed"
- risk: "low" | "medium" | "high" | "critical"
- subsystem: which part of the codebase this task affects

If the plan does not explicitly provide a field, omit it — defaults will be applied.
Risk inference: tasks touching shared/util code = "high"; tasks with runtime
behavior changes = default "medium"; docs-only = "low".

Example output for a 3-task plan where task-3 depends on task-1:

{
  "groups": [["task-1", "task-2"], ["task-3"]],
  "tasks": {
    "task-1": {
      "id": "task-1",
      "description": "## Task 1: Create Add Function\\n\\n**Depends on:** none\\n\\nCreate a function...",
      "depends_on": [],
      "files": ["src/math.js"],
      "tests": ["tests/test_math.js"],
      "verification": ["node tests/test_math.js"],
      "risk": "low",
      "subsystem": "core"
    },
    "task-2": {
      "id": "task-2",
      "description": "## Task 2: Create Greet Function\\n\\n**Depends on:** none\\n\\n...",
      "depends_on": [],
      "files": ["src/greet.js"],
      "tests": ["tests/test_greet.js"],
      "verification": ["node tests/test_greet.js"],
      "risk": "low",
      "subsystem": "core"
    },
    "task-3": {
      "id": "task-3",
      "description": "## Task 3: Integration\\n\\n**Depends on:** task-1\\n\\n...",
      "depends_on": ["task-1"],
      "files": ["src/main.js"],
      "tests": ["tests/test_integration.js"],
      "verification": ["node tests/test_integration.js"],
      "risk": "medium",
      "subsystem": "core"
    }
  }
}`,
  agentOpts('parse-plan', 'Parse Plan', TASKS_SCHEMA),
)

log(`Parsed: ${parsed.groups.length} groups, ${Object.keys(parsed.tasks).length} tasks`)

// ── Validate parsed plan ──────────────────────────────────────────────

// Apply defaults for missing metadata fields
for (const tid of Object.keys(parsed.tasks)) {
  const t = parsed.tasks[tid]
  if (!t.depends_on) t.depends_on = TASK_METADATA_DEFAULTS.depends_on
  if (!t.files) t.files = TASK_METADATA_DEFAULTS.files
  if (!t.tests) t.tests = TASK_METADATA_DEFAULTS.tests
  if (!t.verification) t.verification = TASK_METADATA_DEFAULTS.verification
  if (!t.acceptance_refs) t.acceptance_refs = TASK_METADATA_DEFAULTS.acceptance_refs
  if (!t.risk) t.risk = TASK_METADATA_DEFAULTS.risk
  if (!t.subsystem) t.subsystem = TASK_METADATA_DEFAULTS.subsystem
  if (!t.runtime_evidence_required) t.runtime_evidence_required = TASK_METADATA_DEFAULTS.runtime_evidence_required
}

const planValidation = validateParsedPlan(parsed)
if (!planValidation.valid) {
  const errorSummary = planValidation.errors.map(e => `[${e.code}] ${e.detail}`).join('\n')
  log(`Plan validation FAILED — ${planValidation.errors.length} error(s):\n${errorSummary}`)
  return {
    spec: { path: spec.spec_path, review_passed: specReview.passed },
    plan: { path: planResult.plan_path, review_passed: planReview.passed, task_count: planResult.task_count },
    execute: { completed: [], blocked: [] },
    gates: CANONICAL_GATES.map((_, i) => ({
      gate: i + 1, passed: false,
      detail: 'Skipped — plan validation failed',
      fix_applied: '',
    })),
    all_passed: false,
    validation_errors: planValidation.errors,
  }
}
log('Plan validation passed')

// ── Phase 8: Execute ─────────────────────────────────────────────────

phase('Execute')
log('Delegating to execute-plan workflow...')

const executeResult = await workflow(
  { scriptPath: execute_plan_script_path },
  {
    groups: parsed.groups,
    tasks: parsed.tasks,
    worktree: worktree,
    model_tasks: model_tasks,
  },
)

log(`Execute: ${executeResult.completed.length} completed, ${executeResult.blocked.length} blocked`)

// ── Phase 9: Gates ───────────────────────────────────────────────────

phase('Gates')
const gates = []

function priorPassed() { return gates.length === 0 || gates[gates.length - 1].passed }

// Gates 1 & 2: verified by execute phase results — no agent needed
const g1Passed = executeResult.blocked.length === 0
gates.push({
  gate: 1,
  passed: g1Passed,
  detail: `${executeResult.completed.length} completed, ${executeResult.blocked.length} blocked`,
  fix_applied: '',
})

const g2Passed = executeResult.completed.length > 0 &&
  executeResult.completed.every(r => r.code_passed)
gates.push({
  gate: 2,
  passed: g2Passed,
  detail: g2Passed ? 'All reviews passed' : 'Some reviews have unresolved issues',
  fix_applied: '',
})

// Gate 3: test suite passes
if (priorPassed()) {
  let passed = false
  let detail = ''
  let iters = 0

  while (!passed && iters < GATE_RETRIES) {
    const r = await agent(
      `Run the project's full test suite. Read package.json or test config
to find the command, then run it. If tests fail: read the output, fix the
implementation (not tests unless expectations are wrong), run again.
Report: passed (all green) or failed.`,
      agentOpts('gate-3-tests', 'Gates', GATE_RESULT),
    )
    passed = r.passed
    detail = r.detail
    iters++
  }

  gates.push({ gate: 3, passed, detail, fix_applied: iters > 1 ? `${iters} attempts` : '' })
}

// Gate 4: runtime evidence
if (priorPassed()) {
  const r = await agent(
    `Verify the implementation works at runtime.
1. If this is a runnable project: build and run a smoke test
   (start server, run CLI, etc.), capture exit code/output/crashes
2. If library/config-only: report as unverifiable (auto-pass)
Report what you observed.`,
    agentOpts('gate-4-runtime', 'Gates', GATE_RESULT),
  )
  gates.push(r)
}

// Gate 5: verify against spec
if (priorPassed()) {
  const r = await agent(
    `Verify the implementation against the spec at ${specPath}.
Read the spec line by line. For each requirement, find the code that satisfies it.
Report: passed (every requirement verified) or failed with specific gaps.`,
    agentOpts('gate-5-spec-verify', 'Gates', GATE_RESULT),
  )
  gates.push(r)
}

// Gate 6: final code review
if (priorPassed()) {
  let passed = false
  let iters = 0

  const review = await agent(
    `Final code review of all changes on this branch.
Run \`git diff main...HEAD\` (or the base branch) to see the diff.
Review for: correctness bugs, dead code, missing error handling, security issues.`,
    agentOpts('gate-6-final-review', 'Gates', GATE_RESULT),
  )
  passed = review.passed

  while (!passed && iters < RETRIES) {
    await agent(
      `Fix these final review issues: ${review.detail}
Minimal fixes — do not refactor.`,
      agentOpts(`fix-final-r${iters + 1}`, 'Gates', { type: 'object' }),
    )
    const re = await agent(
      'Re-review: verify previous issues fixed. No new issues.',
      agentOpts(`gate-6-r${iters + 1}`, 'Gates', GATE_RESULT),
    )
    passed = re.passed
    iters++
  }

  gates.push({
    gate: 6, passed,
    detail: passed ? 'Final review passed' : `Issues remain after ${iters} fixes`,
    fix_applied: iters > 0 ? `${iters} fix rounds` : '',
  })
}

// Gate 7: git clean
if (priorPassed()) {
  const r = await agent(
    `Run \`git status --porcelain\`. If dirty: commit changes with appropriate messages.
If clean: report passed.`,
    agentOpts('gate-7-git-clean', 'Gates', GATE_RESULT),
  )
  gates.push(r)
}

// Fill remaining gates as skipped
while (gates.length < 7) {
  gates.push({
    gate: gates.length + 1,
    passed: false,
    detail: 'Skipped — earlier gate not passed',
    fix_applied: '',
  })
}

// ── Return complete results ──────────────────────────────────────────

return {
  spec: { path: spec.spec_path, review_passed: specReview.passed },
  plan: { path: planResult.plan_path, review_passed: planReview.passed, task_count: planResult.task_count },
  execute: executeResult,
  gates,
  all_passed: gates.every(g => g.passed),
}
