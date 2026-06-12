// Invoked by the auto-mode dynamic workflow for the full-auto pipeline mode.
// Orchestrates: scope → research → optional design → synthesize spec → review spec → write plan →
// review plan → parse plan → execute → gates.
//
// See SKILL.md for launch instructions.

export const meta = {
  name: 'full-auto-pipeline',
  description:
    'Full auto-mode pipeline: research → optional design → spec → plan review → parse plan → execute → gates',
  args_schema: {
    state_file: { type: 'string', description: 'Path to state.json for this run' },
    audit_dir: { type: 'string', description: 'Directory for audit event logs' },
    evidence_dir: { type: 'string', description: 'Directory for runtime evidence artifacts' },
    resume_from: {
      type: 'object',
      properties: {
        revision: { type: 'number' },
        cursor: { type: 'object' },
        next_entrypoint: { type: 'string' },
      },
    },
    retry_policy: {
      type: 'object',
      properties: {
        review_cap: { type: 'number' },
        gate_retries: { type: 'number' },
      },
    },
    allowed_escalation_models: { type: 'array', items: { type: 'string' } },
    allow_commit: { type: 'boolean' },
    flow_state_cli_path: { type: 'string', description: 'Path to hooks/scripts/flow-state.py CLI' },
  },
  result_schema: {
    state_file: { type: 'string' },
    audit_events: { type: 'array' },
    evidence_dir: { type: 'string' },
    resume_cursor: { type: 'object' },
  },
  phases: [
    { title: 'Scope', detail: 'Determine research angles' },
    { title: 'Research', detail: 'Parallel research per angle' },
    { title: 'Design', detail: 'Conditionally create UI/UX design artifacts' },
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
  model_tasks,
  max_retries,
  // State-writer integration
  state_file,
  audit_dir,
  evidence_dir,
  resume_from,
  retry_policy,
  allowed_escalation_models,
  allow_commit,
  flow_state_cli_path,
} = args

const REVIEW_RETRY_CAP_DEFAULT = 5
const GATE_RETRY_CAP_DEFAULT = 10

if (!task || typeof task !== 'string') {
  throw new Error('full-auto-pipeline: args.task is required (string describing the task)')
}

const specId = task
  .replace(/[^a-z0-9]+/gi, '-')
  .replace(/^-+|-+$/g, '')
  .toLowerCase()
  .slice(0, 60)
const specPath = `${specs_dir}/${specId}.md`
const planPath = `${plans_dir}/${specId}-plan.md`
const designSlug = sanitizeDesignSlug(specId || task)
const designDir = `.claude/auto/${designSlug}/design`
const designPaths = {
  ui_research: `${designDir}/ui-research.md`,
  design: 'DESIGN.md',
  design_review: `${designDir}/design-review.md`,
}
const designWriteTargets = {
  ui_research: worktree ? `${worktree}/${designPaths.ui_research}` : designPaths.ui_research,
  design: worktree ? `${worktree}/${designPaths.design}` : designPaths.design,
  design_review: worktree ? `${worktree}/${designPaths.design_review}` : designPaths.design_review,
}

const RETRIES = max_retries || 5
const REVIEW_RETRY_CAP = (retry_policy && retry_policy.review_cap) || REVIEW_RETRY_CAP_DEFAULT
const GATE_RETRIES = (retry_policy && retry_policy.gate_retries) || GATE_RETRY_CAP_DEFAULT

const PHASE_ORDER = [
  'scope', 'research', 'design', 'synthesize_spec', 'review_spec',
  'write_plan', 'review_plan', 'parse_plan', 'execute', 'gates', 'finalize',
]

function sanitizeDesignSlug(value) {
  let slug = String(value || '').toLowerCase().trim()
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/-{2,}/g, '-')
    .replace(/^-+|-+$/g, '')
  if (!slug || slug === '.' || slug === '..') slug = 'unnamed'
  if (['con', 'prn', 'aux', 'nul', 'com1', 'lpt1'].includes(slug)) slug = `task-${slug}`
  return slug.slice(0, 60).replace(/-+$/g, '') || 'unnamed'
}

// ── Resume from state ─────────────────────────────────────────────────
// When resume_from is provided, determine which phases to skip based on cursor.
// The resume_cursor.phase tells us the last active phase. Phases before it
// are already complete and should be skipped. result_replay lists task IDs
// that were already passed and should not be re-run.

const resumeCursor = (resume_from && resume_from.cursor) || {}
const resumeSummary = (resume_from && resume_from.summary) || {}
const resumePhase = resumeCursor.phase || null
const resumePhaseIndex = resumePhase ? PHASE_ORDER.indexOf(resumePhase) : -1
const resumeInvalidatedTasks = Object.keys((resume_from && resume_from.invalidated_tasks) || {})
const resumeTaskReplay = ((resume_from && resume_from.result_replay) || [])
  .filter(taskId => !resumeInvalidatedTasks.includes(taskId))

let scope = resumeSummary.scope || null
let allFindings = resumeSummary.research_findings || []
let spec = { spec_path: resumeCursor.spec_path || resumeSummary.spec_path || specPath, summary: '' }
let specReview = { passed: true, issues: [], summary: 'Replayed from resume state' }
let planResult = {
  plan_path: resumeCursor.plan_path || resumeSummary.plan_path || planPath,
  task_count: resumeSummary.progress && resumeSummary.progress.tasks_total || 0,
  dependency_groups: resumeSummary.groups && resumeSummary.groups.length || 0,
  summary: 'Replayed from resume state',
}
let planReview = { passed: true, issues: [], summary: 'Replayed from resume state' }
let parsed = {
  groups: resumeSummary.groups || [],
  tasks: resumeSummary.tasks || {},
}
let executeResult = resumeSummary.execute_result || { completed: [], blocked: [], final_review: null }
let designContext = (resumeCursor && resumeCursor.design) || (resumeSummary && resumeSummary.design) || defaultDesignContext('not_run', 'Non-UI task: design stage has not run yet. Design stage skipped to avoid retrofitting UI/UX work.')
if (resumeTaskReplay.length && Object.keys(parsed.tasks).length === 0) {
  parsed.tasks = Object.fromEntries(resumeTaskReplay.map(id => [id, { id, description: `Replayed task ${id}` }]))
}

function shouldSkipPhase(phaseName) {
  if (!resumePhase) return false
  const phaseIdx = PHASE_ORDER.indexOf(phaseName)
  return phaseIdx >= 0 && phaseIdx < resumePhaseIndex
}

function isResumeForPhase(phaseName) {
  return resumePhase === phaseName
}

// Replay helper: check if a task was already passed in prior run
function isTaskReplayed(taskId) {
  return resumeTaskReplay.includes(taskId)
}

// ── State writer integration ──────────────────────────────────────────

let currentRevision = (resume_from && resume_from.revision) || 0
const flowStateCliPath = flow_state_cli_path || null

async function flowState(cmd, data) {
  if (!flowStateCliPath) return { ok: true }
  let argv = []
  if (cmd === 'update') {
    argv = ['update', '--state-file', state_file, '--patch-json', JSON.stringify(data)]
    if (currentRevision !== null && currentRevision !== undefined) {
      argv.push('--expected-revision', String(currentRevision))
    }
  } else if (cmd === 'event') {
    const { type, ...rest } = data
    argv = ['event', '--state-file', state_file, '--type', type || 'event', '--json-data', JSON.stringify(rest)]
  } else if (cmd === 'manifest') {
    argv = ['manifest', '--state-file', state_file, '--patch-json', JSON.stringify(data)]
  } else if (cmd === 'resume') {
    argv = ['resume', '--state-file', state_file]
  } else if (cmd === 'validate') {
    argv = ['validate', '--state-file', state_file]
  } else if (cmd === 'snapshot') {
    argv = ['snapshot', '--state-file', state_file, '--reason', data.reason || 'workflow']
  } else {
    return { ok: false, errors: [`Unsupported flow-state command: ${cmd}`] }
  }

  const FLOW_STATE_RESULT = {
    type: 'object', additionalProperties: true,
    properties: { ok: { type: 'boolean' }, revision: { type: 'number' }, errors: { type: 'array', items: { type: 'string' } } },
    required: ['ok'],
  }

  const result = await agent(
    `Run the flow-state CLI and return its JSON stdout exactly as structured data.

CLI path: ${flowStateCliPath}
Arguments JSON: ${JSON.stringify(argv)}

Use Python to execute the CLI with these arguments. Do not edit files except through the CLI. If the command fails, return ok=false with errors from stdout/stderr.`,
    { label: `flow-state:${cmd}`, schema: FLOW_STATE_RESULT },
  )
  if (result && result.ok && typeof result.revision === 'number') {
    currentRevision = result.revision
  }
  return result || { ok: false, errors: ['flowState returned no result'] }
}

const auditEvents = []

// ── Contract constants ────────────────────────────────────────────────

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

// Gate name constants matching CANONICAL_GATES order
const GATE_TASKS_EXECUTED = 'tasks_executed'
const GATE_REVIEWS_PASSED = 'reviews_passed'
const GATE_TESTS_PASS = 'tests_pass'
const GATE_RUNTIME_EVIDENCE = 'runtime_evidence'
const GATE_SPEC_VERIFIED = 'spec_verified'
const GATE_FINAL_REVIEW = 'final_review'
const GATE_GIT_CLEAN = 'git_clean'

const GATE_NAMES = [
  GATE_TASKS_EXECUTED, GATE_REVIEWS_PASSED, GATE_TESTS_PASS,
  GATE_RUNTIME_EVIDENCE, GATE_SPEC_VERIFIED, GATE_FINAL_REVIEW,
  GATE_GIT_CLEAN,
]

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
  if (explicitFlag === false && reviewStage !== 'final_review') return false
  const key = reviewStage === 'final_review' ? 'any' : taskRisk
  const table = REVIEW_THRESHOLD[reviewStage]
  if (!table || !table[key]) return severity === 'Critical' || severity === 'High'
  const rule = table[key][severity]
  if (rule === true) return true
  if (rule === false) return false
  return explicitFlag === true
}

function validateGateSet(gateStates) {
  const reported = Object.keys(gateStates)
  const missing = CANONICAL_GATES.filter(g => !reported.includes(g))
  return { valid: missing.length === 0, missing }
}

function makeGateRecord(name, passed, detail, extra) {
  const now = new Date().toISOString()
  return {
    name,
    passed,
    detail: detail || '',
    iterations: (extra && extra.iterations) || 1,
    last_failure: (extra && extra.last_failure) || null,
    last_fix: (extra && extra.last_fix) || null,
    evidence_paths: (extra && extra.evidence_paths) || [],
    updated_at: now,
    next_action: passed ? 'proceed' : ((extra && extra.next_action) || 'retry'),
    fix_applied: (extra && extra.fix_applied) || '',
    ...(extra && extra.manifest ? { manifest: extra.manifest } : {}),
  }
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

const DESIGN_CLASSIFICATION_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    design_applicable: { type: 'boolean' },
    classification: { type: 'string', enum: ['ui_ux_frontend_visual', 'non_ui'] },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    evidence: { type: 'array', items: { type: 'string' } },
    skip_reason: { type: 'string' },
  },
  required: ['design_applicable', 'classification', 'confidence', 'evidence', 'skip_reason'],
}

const DESIGN_ARTIFACT_SCHEMA = {
  type: 'object', additionalProperties: false,
  properties: {
    status: { type: 'string', enum: ['DONE', 'BLOCKED'] },
    summary: { type: 'string' },
    artifact_paths: {
      type: 'object', additionalProperties: false,
      properties: {
        ui_research: { type: 'string' },
        design: { type: 'string' },
        design_review: { type: 'string' },
      },
      required: ['ui_research', 'design', 'design_review'],
    },
    blocker_detail: { type: 'string' },
  },
  required: ['status', 'summary', 'artifact_paths'],
}

const DESIGN_CLASSIFICATION_CRITERIA = `Run design only for explicit UI/UX/frontend visual changes: page, view, component visuals, layout, styling, accessibility interaction, keyboard/focus behavior, visual states, user flow screens, form validation UX, UI copy/content, visual bugfixes, or product UI asset placement.
Skip backend/API/DB/auth/data-only, CLI/config/docs-only, prompt-workflow, tests, refactor/internal architecture, nonvisual bugfixes, and weak ambiguous component/view/page mentions without explicit visual/interface delta.
Ambiguous cases default to design_applicable=false with skip_reason starting exactly: Non-UI task:`

function defaultDesignContext(status, skipReason) {
  return {
    status: status || 'skipped',
    design_applicable: false,
    classification: 'non_ui',
    confidence: 'low',
    evidence: [],
    skip_reason: skipReason || 'Non-UI task: no explicit UI/UX/frontend visual change requested. Design stage skipped to avoid retrofitting UI/UX work.',
    paths: designPaths,
  }
}

function normalizeDesignClassification(result) {
  if (!result || typeof result.design_applicable !== 'boolean') return null
  if (result.design_applicable && result.classification !== 'ui_ux_frontend_visual') return null
  if (!result.design_applicable && result.classification !== 'non_ui') return null
  if (!result.design_applicable && !String(result.skip_reason || '').startsWith('Non-UI task:')) return null
  if (result.design_applicable && (!Array.isArray(result.evidence) || result.evidence.length === 0)) return null
  return result
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


// ── Execute-phase helpers (merged from execute-plan) ────────────────────────

const COMMAND_EXECUTION_PRIMITIVE = 'workflow_agent_only'
const ENFORCEMENT_MODE = 'prompt_only'

function asArray(value) {
  return Array.isArray(value) ? value : []
}

function pickCanonical(source, fallback, field, warnings) {
  if (source && Object.prototype.hasOwnProperty.call(source, field)) {
    if (fallback && Object.prototype.hasOwnProperty.call(fallback, field) && JSON.stringify(source[field]) !== JSON.stringify(fallback[field])) {
      warnings.push('resume_state_patch_preferred: ' + field)
    }
    return source[field]
  }
  return fallback && Object.prototype.hasOwnProperty.call(fallback, field) ? fallback[field] : undefined
}

function normalizeResumeState(saved) {
  const input = saved || {}
  const top = input.execute_result || input.result || input
  const patch = top.state_patch || input.state_patch || {}
  const warnings = []
  const get = field => pickCanonical(patch, top, field, warnings)
  return {
    result_replay: asArray(input.result_replay || top.result_replay),
    warnings,
    final_review_run: get('final_review_run') === true,
    final_review: get('final_review') || null,
    final_review_evidence: asArray(get('final_review_evidence')),
    final_review_blocking_issues: asArray(get('final_review_blocking_issues')),
    unresolved_final_review_issues: asArray(get('unresolved_final_review_issues') || get('final_review_unresolved_issue_ids')),
    final_review_blocked: get('final_review_blocked') === true,
    enforcement_mode: get('enforcement_mode') || ENFORCEMENT_MODE,
    base_ref: get('base_ref') || '',
    base_sha: get('base_sha') || '',
    head_sha: get('head_sha') || '',
    dirty: get('dirty') === true,
    diff_command: get('diff_command') || '',
    diff_files: asArray(get('diff_files')),
    diff_verified: get('diff_verified') === true,
    diff_truncated: get('diff_truncated') === true,
    evidence_dir: get('evidence_dir') || '',
    iterations: get('iterations') || 0,
    tasks_stale_after_final_fix: asArray(get('tasks_stale_after_final_fix')),
  }
}

// ── Diff anchor resolution (helper-only; no command primitive) ───────────

function isValidSha(value) {
  return typeof value === 'string' && /^[0-9a-f]{7,40}$/i.test(value)
}

function anchorError(code, detail) {
  return { code, detail }
}

function gitAnchorError(args, task, code) {
  const git = (args && args.git) || (task && task.git) || {}
  if (!git) return null
  if (git[code]) return anchorError(code, git[code] === true ? code : git[code])
  return null
}

function resolveDiffAnchors(args, task, impl, stage) {
  const metadata = {
    stage,
    enforcement_mode: ENFORCEMENT_MODE,
    command_primitive: COMMAND_EXECUTION_PRIMITIVE,
    verified: false,
    base_sha: '',
    base_ref: '',
    anchor_error: null,
  }

  const explicit = args && args.base_sha
  if (explicit) {
    if (!isValidSha(explicit)) return { ...metadata, source: 'explicit_args_base_sha', anchor_error: anchorError('invalid_sha', 'args.base_sha') }
    return { ...metadata, source: 'explicit_args_base_sha', base_sha: explicit }
  }

  const taskBase = task && (task.base_sha || task.captured_base_sha || task.git_base_sha)
  if (taskBase) {
    if (!isValidSha(taskBase)) return { ...metadata, source: 'task_captured_base_sha', anchor_error: anchorError('invalid_sha', 'task base_sha') }
    return { ...metadata, source: 'task_captured_base_sha', base_sha: taskBase }
  }

  const git = (args && args.git) || (task && task.git) || {}
  const defaultRef = (args && (args.default_branch || args.default_ref)) || git.default_branch || git.default_ref
  const baseRef = (args && args.base_ref) || defaultRef || 'main'
  const baseRefSource = defaultRef && !(args && args.base_ref) ? 'default_branch_ref' : 'base_ref'
  const repoError =
    gitAnchorError(args, task, 'no_repo') ||
    gitAnchorError(args, task, 'merge_conflict') ||
    gitAnchorError(args, task, 'detached_head') ||
    gitAnchorError(args, task, 'unborn_or_no_commits') ||
    gitAnchorError(args, task, 'missing_base_ref') ||
    gitAnchorError(args, task, 'shallow_or_missing_base')

  if (!repoError) {
    return {
      ...metadata,
      source: 'merge_base_ref',
      base_ref: baseRef,
      base_ref_source: baseRefSource,
      anchor_error: anchorError('prompt_only_merge_base_unverified', 'merge-base requires command primitive'),
    }
  }

  const promptBase = impl && impl.base_sha
  if (promptBase) {
    if (!isValidSha(promptBase)) return { ...metadata, source: 'prompt_only_impl_base_sha', anchor_error: anchorError('invalid_sha', 'impl.base_sha') }
    return { ...metadata, source: 'prompt_only_impl_base_sha', base_sha: promptBase, anchor_error: repoError }
  }

  return { ...metadata, source: 'unverified', base_ref: baseRef, base_ref_source: baseRefSource, anchor_error: repoError }
}

function diffAnchorPrompt(task, impl, stage) {
  const src = typeof args === 'undefined' ? {} : args
  const anchor = resolveDiffAnchors(src, task, impl, stage)
  return '\n\n## Diff Anchor Metadata\n\n' + JSON.stringify(anchor, null, 2)
}

const DEFAULT_DIFF_BODY_LIMIT = 60000

function truncateText(value, limit) {
  const text = typeof value === 'string' ? value : ''
  const max = limit || DEFAULT_DIFF_BODY_LIMIT
  if (text.length <= max) return { text, truncated: false, original_length: text.length }
  return { text: text.slice(0, max), truncated: true, original_length: text.length }
}

function splitNameStatus(value) {
  if (!value) return []
  return value.split(/\r?\n/).filter(Boolean)
}

function nameStatusFiles(line) {
  const parts = line.split('\t')
  const status = parts[0] || ''
  if (status[0] === 'R' || status[0] === 'C') return parts.slice(1, 3).filter(Boolean)
  return parts.slice(1).filter(Boolean)
}

function extractStatusMetadata(lines, diffBody) {
  const metadata = { binary: [], renamed: [], deleted: [] }
  for (const line of lines) {
    const parts = line.split('\t')
    const status = parts[0] || ''
    if (status[0] === 'R') metadata.renamed.push({ from: parts[1] || '', to: parts[2] || '', status })
    if (status[0] === 'D') metadata.deleted.push(parts[1] || '')
    if (status === '-' && parts[2]) metadata.binary.push(parts[2])
  }
  const binaryRe = /Binary files (?:a\/)?(.+?) and (?:b\/)?(.+?) differ/g
  let match
  while ((match = binaryRe.exec(diffBody || '')) !== null) {
    const path = match[2] || match[1]
    if (path && !metadata.binary.includes(path)) metadata.binary.push(path)
  }
  return metadata
}

function buildDiffScopeEvidence(scope, anchor) {
  const source = (anchor && anchor[scope]) || {}
  const limit = (anchor && anchor.max_diff_chars) || DEFAULT_DIFF_BODY_LIMIT
  const body = truncateText(source.diff || source.body || '', limit)
  const summary = truncateText(source.summary || source.diff_summary || source.stat || '', limit)
  const nameStatus = splitNameStatus(source.name_status || source.nameStatus || '')
  const files = []
  for (const line of nameStatus) {
    for (const file of nameStatusFiles(line)) files.push(file)
  }
  return {
    ok: source.ok === true,
    name_status: nameStatus,
    files,
    diff_body: body.text,
    diff_summary: summary.text,
    truncated: body.truncated || summary.truncated,
    body_truncated: body.truncated,
    summary_truncated: summary.truncated,
    original_body_length: body.original_length,
    error: source.error || null,
  }
}

function mergeSpecialStatuses(a, b) {
  return {
    binary: [...a.binary, ...b.binary],
    renamed: [...a.renamed, ...b.renamed],
    deleted: [...a.deleted, ...b.deleted],
  }
}

function collectDiffEvidence(anchor) {
  const committed = buildDiffScopeEvidence('committed', anchor || {})
  const worktree = buildDiffScopeEvidence('worktree', anchor || {})
  const committedSpecial = extractStatusMetadata(committed.name_status, committed.diff_body)
  const worktreeSpecial = extractStatusMetadata(worktree.name_status, worktree.diff_body)
  const command_errors = []
  if (committed.error) command_errors.push({ scope: 'committed', error: committed.error })
  if (worktree.error) command_errors.push({ scope: 'worktree', error: worktree.error })
  if (anchor && anchor.anchor_error) command_errors.push({ scope: 'anchor', error: anchor.anchor_error })
  const scope_complete = committed.ok && worktree.ok && !command_errors.length
  const worktreeIncluded = worktree.name_status.length > 0 || worktree.diff_body.length > 0
  const diffFiles = [...new Set([...committed.files, ...worktree.files])]
  const verified = scope_complete
  const truncated = committed.truncated || worktree.truncated
  return {
    stage: anchor && anchor.stage,
    enforcement_mode: ENFORCEMENT_MODE,
    command_primitive: COMMAND_EXECUTION_PRIMITIVE,
    base_sha: (anchor && anchor.base_sha) || '',
    base_ref: (anchor && anchor.base_ref) || '',
    head_sha: (anchor && anchor.head_sha) || '',
    dirty: !!(anchor && anchor.dirty),
    includes_worktree_diff: worktreeIncluded,
    worktree_diff_included: worktreeIncluded,
    scope_complete,
    verified_diff: verified,
    diff_verified: verified,
    diff_command: (anchor && anchor.command) || '',
    diff_files: diffFiles,
    diff_truncated: truncated,
    committed_diff: committed,
    worktree_diff: worktree,
    special_statuses: mergeSpecialStatuses(committedSpecial, worktreeSpecial),
    truncated,
    command_errors,
  }
}

function controllerCommandsExist(args) {
  const git = (args && args.git) || {}
  if (git.controller_commands_available === false) return false
  return !!(git.controller_commands_available || git.head_sha || git.dirty !== undefined || git.attempts)
}

function captureAttemptBase(args, task, ctx, label) {
  if (!controllerCommandsExist(args)) return null
  const git = (args && args.git) || {}
  const baseSha = git.head_sha || git.base_sha || ''
  if (!task.task_attempt_base_sha && !task.task_attempt_base_capture_failed) {
    task.task_attempt_base_sha = baseSha
    task.task_attempt_base_dirty = !!git.dirty
    if (!baseSha) task.task_attempt_base_capture_failed = 'missing_controller_head_sha'
  }
  const capture = {
    label,
    task_attempt_base_sha: task.task_attempt_base_sha || '',
    task_attempt_base_dirty: !!task.task_attempt_base_dirty,
    task_attempt_base_capture_failed: task.task_attempt_base_capture_failed || '',
  }
  ctx.task_attempt_base_sha = capture.task_attempt_base_sha
  ctx.task_attempt_base_dirty = capture.task_attempt_base_dirty
  ctx.task_attempt_base_capture_failed = capture.task_attempt_base_capture_failed
  return capture
}

function recordAttemptDiffEvidence(args, task, ctx, label) {
  const git = (args && args.git) || {}
  const attempts = git.attempts || {}
  const attempt = attempts[label] || {}
  const baseSha = (task && task.task_attempt_base_sha) || (ctx && ctx.task_attempt_base_sha) || ''
  const hasAttempt = !!attempt.head_sha || !!attempt.committed || !!attempt.worktree || !!attempt.command
  const anchor = hasAttempt ? {
    stage: label,
    base_sha: baseSha,
    head_sha: attempt.head_sha || git.head_sha || '',
    dirty: attempt.dirty !== undefined ? attempt.dirty : !!git.dirty,
    command: attempt.command || '',
    committed: attempt.committed || {},
    worktree: attempt.worktree || {},
    anchor_error: attempt.anchor_error || null,
    max_diff_chars: attempt.max_diff_chars,
    command_results: attempt.command_results || [],
    evidence_paths: attempt.evidence_paths || [],
    path_exists: attempt.path_exists || {},
  } : {
    stage: label,
    base_sha: baseSha,
    head_sha: git.head_sha || '',
    dirty: !!git.dirty,
    committed: { ok: false, error: 'prompt_only_no_controller_diff' },
    worktree: { ok: false, error: 'prompt_only_no_controller_diff' },
  }
  const evidence = collectDiffEvidence(anchor)
  const entry = {
    label,
    ...evidence,
    command_results: anchor.command_results || [],
    evidence_paths: anchor.evidence_paths || [],
    path_exists: anchor.path_exists || {},
  }
  if (ctx) ctx.attempt_diff_evidence = [...(ctx.attempt_diff_evidence || []), entry]
  if (task && task !== ctx) task.attempt_diff_evidence = [...(task.attempt_diff_evidence || []), entry]
  return entry
}

// ── (REVIEW_THRESHOLD and isIssueBlocking already defined above) ──────

const REVIEW_SEVERITY_ALIASES = {
  critical: 'Critical', high: 'High', important: 'Important', medium: 'Important', minor: 'Minor', low: 'Minor', info: 'Info', informational: 'Info', nit: 'Minor',
}

function normalizeReviewSeverity(value) {
  const raw = String(value || '').trim()
  return REVIEW_SEVERITIES.includes(raw) ? raw : (REVIEW_SEVERITY_ALIASES[raw.toLowerCase()] || 'Info')
}

function normalizeReviewCategory(value, stage) {
  const raw = String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
  if (raw) return raw
  if (stage === 'spec_review') return 'requirements'
  if (stage === 'code_review' || stage === 'final_review') return 'code_quality'
  return 'review'
}

function normalizeIssueLocation(issue) {
  const file = String((issue && issue.file) || '').trim()
  const lineNumber = Number(issue && issue.line)
  const line = Number.isFinite(lineNumber) && lineNumber > 0 ? lineNumber : undefined
  const location = String((issue && issue.location) || (file ? file + (line ? ':' + line : '') : '')).trim()
  const reason = String((issue && issue.location_unavailable_reason) || '').trim()
  return {
    file,
    line,
    location,
    location_unavailable_reason: file || location ? '' : (reason || 'not_provided_by_reviewer'),
  }
}

function stableStringify(value) {
  if (Array.isArray(value)) return '[' + value.map(stableStringify).join(',') + ']'
  if (value && typeof value === 'object') {
    return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + stableStringify(value[k])).join(',') + '}'
  }
  return JSON.stringify(value == null ? '' : value)
}

function fnv1aHash(value) {
  let hash = 0x811c9dc5
  const text = String(value || '')
  for (let i = 0; i < text.length; i++) {
    hash ^= text.charCodeAt(i)
    hash = Math.imul(hash, 0x01000193) >>> 0
  }
  return hash.toString(36).padStart(7, '0')
}

function issueHashInput(issue, context) {
  const stage = (context && context.stage) || 'review'
  const location = normalizeIssueLocation(issue)
  return stableStringify({
    v: 1,
    stage,
    severity: normalizeReviewSeverity(issue && issue.severity),
    category: normalizeReviewCategory(issue && issue.category, stage),
    file: location.file,
    line: location.line || '',
    location: location.location,
    description: String((issue && issue.description) || '').trim().toLowerCase().replace(/\s+/g, ' '),
  })
}

function deriveIssueId(issue, context) {
  const stage = String((context && context.stage) || 'review').replace(/[^a-z0-9_\-]+/gi, '_')
  const taskId = String((context && (context.task_id || context.taskId || context.task)) || (stage === 'final_review' ? 'final' : 'unknown')).replace(/[^a-z0-9_\-]+/gi, '_')
  const severity = normalizeReviewSeverity(issue && issue.severity).toLowerCase()
  const base = 'amr1:' + stage + ':' + taskId + ':' + severity + ':' + fnv1aHash(issueHashInput(issue || {}, context || {}))
  const counts = context && context.issue_id_counts
  if (!counts) return base
  const n = counts[base] || 0
  counts[base] = n + 1
  return n === 0 ? base : base + '-' + (n + 1)
}

function normalizeReviewIssues(review, context) {
  const ctx = { ...(context || {}), issue_id_counts: {} }
  const seen = {}
  const prior = (context && context.prior_issues) || []
  const priorByKey = {}
  for (const oldIssue of prior) priorByKey[issueHashInput(oldIssue, ctx)] = oldIssue.id || oldIssue.prior_issue_id || ''
  const issues = ((review && review.issues) || []).map(raw => {
    const severity = normalizeReviewSeverity(raw && raw.severity)
    const category = normalizeReviewCategory(raw && raw.category, ctx.stage)
    const location = normalizeIssueLocation(raw || {})
    const issue = { ...(raw || {}), severity, category, ...location }
    const key = issueHashInput(issue, ctx)
    issue.id = issue.id || deriveIssueId(issue, ctx)
    if (!issue.prior_issue_id && priorByKey[key]) issue.prior_issue_id = priorByKey[key]
    if (seen[key] && !issue.duplicate_of) issue.duplicate_of = seen[key]
    if (!seen[key]) seen[key] = issue.id
    if (issue.prior_issue_id && issue.prior_issue_id !== issue.id && !issue.supersedes) issue.supersedes = issue.prior_issue_id
    return issue
  })
  return { ...(review || {}), issues }
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
      let label = ''
      if (rung === 'schema_retry') {
        label = 'escalate-schema-retry:' + task.id
        captureAttemptBase(args, task, task, label)
        result = await agent(implementPrompt(task),
          agentOpts(label, 'Implement', IMPLEMENT_RESULT))
        recordAttemptDiffEvidence(args, task, task, label)
      } else if (rung === 'self_service_retry') {
        label = 'escalate-self-service:' + task.id
        captureAttemptBase(args, task, task, label)
        result = await agent(selfServicePrompt(task),
          agentOpts(label, 'Implement', IMPLEMENT_RESULT))
        recordAttemptDiffEvidence(args, task, task, label)
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
    base_sha: { type: 'string', description: 'Git base SHA before implementation' },
    head_sha: { type: 'string', description: 'Git head SHA after implementation' },
    commit_sha: { type: 'string', description: 'Optional legacy Git commit SHA (short)' },
    concerns: { type: 'array', items: { type: 'string' }, description: 'If DONE_WITH_CONCERNS or evidence is limited, list each concern' },
    diff_summary: { type: 'string', description: 'Summary of files/diff changed; do not include secrets' },
    acceptance_coverage: { type: 'array', items: { type: 'object', additionalProperties: true }, description: 'Acceptance criteria covered by evidence' },
    unverified_acceptance_refs: { type: 'array', items: { type: 'string' }, description: 'Acceptance refs not directly verified' },
    blocker_detail: { type: 'string', description: 'If BLOCKED: what blocks you, what you tried' },
    verification_results: {
      type: 'array',
      items: {
        type: 'object',
        additionalProperties: true,
        properties: {
          command: { type: 'string' },
          exit_code: { type: 'number' },
          output: { type: 'string' },
        },
        required: ['command'],
      },
      description: 'Agent-run verification command results used when controller evidence is prompt-only',
    },
    verification_commands: { type: 'array', items: { type: 'string' }, description: 'Commands to verify the implementation' },
    evidence_paths: { type: 'array', items: { type: 'string' }, description: 'Paths to evidence artifacts checked by controller when available' },
  },
  required: ['status', 'summary', 'files_modified'],
  allOf: [{
    if: { properties: { status: { enum: ['DONE', 'DONE_WITH_CONCERNS'] } }, required: ['status'] },
    then: { required: [
      'test_results', 'verification_commands', 'verification_results', 'base_sha', 'head_sha',
      'acceptance_coverage', 'unverified_acceptance_refs', 'concerns', 'diff_summary',
    ] },
  }],
}

const FIX_RESULT = {
  ...IMPLEMENT_RESULT,
  properties: {
    ...IMPLEMENT_RESULT.properties,
    fixed_issue_ids: { type: 'array', items: { type: 'string' }, description: 'Prior blocking issue IDs fixed by this targeted retry' },
    targeted_verification: { type: 'array', items: { type: 'object', additionalProperties: true }, description: 'Commands/checks run for each fixed issue ID' },
    verification_failures: { type: 'array', items: { type: 'object', additionalProperties: true }, description: 'Targeted commands/checks that failed' },
    unrelated_files_changed: { type: 'array', items: { type: 'string' }, description: 'Files changed outside allowed targeted fix scope' },
    scope_justifications: { type: 'array', items: { type: 'object', additionalProperties: true }, description: 'Why each changed file belongs to the targeted fix' },
  },
  allOf: [{
    if: { properties: { status: { enum: ['DONE', 'DONE_WITH_CONCERNS'] } }, required: ['status'] },
    then: { required: [
      'test_results', 'verification_commands', 'verification_results', 'base_sha', 'head_sha',
      'acceptance_coverage', 'unverified_acceptance_refs', 'concerns', 'diff_summary',
      'fixed_issue_ids', 'targeted_verification', 'verification_failures', 'unrelated_files_changed', 'scope_justifications',
    ] },
  }],
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
          id: { type: 'string' },
          prior_issue_id: { type: 'string' },
          supersedes: { type: 'string' },
          duplicate_of: { type: 'string' },
          severity: { type: 'string', description: 'Free-form severity; normalized after schema parsing' },
          category: { type: 'string', description: 'Free-form category; normalized after schema parsing' },
          file: { type: 'string' },
          line: { type: ['number', 'string', 'null'], description: 'Line number or free-form line value; normalized after schema parsing' },
          location: { type: 'string' },
          location_unavailable_reason: { type: 'string' },
          description: { type: 'string' },
          blocking: { type: 'boolean' },
        },
        required: ['severity', 'description'],
      },
    },
    summary: { type: 'string' },
    prior_findings_verified: { type: 'array', items: { type: 'object', additionalProperties: true }, description: 'For re-review: every prior blocking issue ID with verification status/evidence' },
    unresolved_issue_ids: { type: 'array', items: { type: 'string' }, description: 'Prior issue IDs still unresolved or repeated' },
    new_issues: { type: 'array', items: { type: 'object', additionalProperties: true }, description: 'New findings introduced by the fix, if any' },
    diff_verified: { type: 'boolean', description: 'Whether controller diff/base metadata was credible and inspected' },
    targeted_verification_credible: { type: 'boolean', description: 'Whether targeted fix verification credibly covers fixed_issue_ids' },
    scope_concerns: { type: 'array', items: { type: 'string' }, description: 'Scope concerns including controller-detected unrelated files' },
  },
  required: ['passed', 'issues', 'summary'],
}

// Contract markers: retry labels remain attempt-indexed fix cycles.
// agentOpts('spec-review:' + id + '-r' + (iterations + 1), 'Spec Review', REVIEW_REREVIEW_RESULT)
// agentOpts('code-review:' + ctx.id + '-r' + (iterations + 1), 'Code Review', REVIEW_REREVIEW_RESULT)
const REVIEW_REREVIEW_RESULT = {
  ...REVIEW_RESULT,
  required: [
    'passed', 'issues', 'summary',
    'prior_findings_verified', 'unresolved_issue_ids', 'new_issues',
    'diff_verified', 'targeted_verification_credible', 'scope_concerns',
  ],
}

// ── (agentOpts already defined above) ──────────────────────────────


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
4. If this task requires art/image assets, read skills/auto-mode/prompts/artist-prompt.md and skills/auto-mode/references/image-generation.md, use scripts/generate-image.py exclusively, verify output files exist, and report manifest/evidence paths. Never claim missing files were generated.
5. Run tests, verify GREEN
6. Commit with: feat(${task.id}): [what you built]
7. Self-review before reporting (see below)

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

For DONE/DONE_WITH_CONCERNS include: test_results, verification_commands, verification_results[], base_sha, head_sha, optional legacy commit_sha, acceptance_coverage, unverified_acceptance_refs, concerns, diff_summary.
Evidence files/summaries must not include secrets, tokens, API keys, credentials, private data, or proprietary logs. Redact before reporting.

Your final response will be parsed as JSON. You MUST return valid JSON.`
}

function latestDiffEvidence(impl, task) {
  const attempts = [
    ...((task && task.attempt_diff_evidence) || []),
    ...((impl && impl.attempt_diff_evidence) || []),
  ]
  return attempts.length ? attempts[attempts.length - 1] : null
}

function diffEvidencePrompt(task, impl, stage) {
  const src = typeof args === 'undefined' ? {} : args
  const anchor = resolveDiffAnchors(src, task, impl, stage)
  const evidence = latestDiffEvidence(impl, task) || collectDiffEvidence(anchor)
  return '\n\n## Controller Diff Evidence\n\n' + JSON.stringify(evidence, null, 2) + '\n\n' +
    (evidence.diff_verified ? 'diff_verified=true. Review this verified diff first.\n' : 'diff_verified=false. State this limitation; files_modified is untrusted; do not expand scope beyond available evidence unless needed.\n') +
    diffAnchorPrompt(task, impl, stage)
}

function collectFinalBranchDiffEvidence(args, finalTask, finalImpl) {
  const git = (args && args.git) || {}
  const final = git.final || git.branch_diff || {}
  const resolved = resolveDiffAnchors(args, finalTask, finalImpl, 'final')
  const anchor = {
    ...resolved,
    stage: 'final',
    head_sha: final.head_sha || git.head_sha || '',
    dirty: final.dirty !== undefined ? final.dirty : !!git.dirty,
    command: final.command || 'git diff --name-status BASE...HEAD && git diff BASE...HEAD',
    committed: final.committed || {},
    worktree: final.worktree || {},
    anchor_error: final.anchor_error || (final.command ? null : resolved.anchor_error) || null,
    max_diff_chars: final.max_diff_chars,
  }
  return collectDiffEvidence(anchor)
}

function finalReviewPrompt(completed, finalTask, finalImpl, priorReview) {
  const branchDiffEvidence = collectFinalBranchDiffEvidence(args, finalTask, finalImpl)
  const completedSummary = (completed || []).map(entry => ({ id: entry.id, files: entry.files || [] }))
  const priorBlocking = ((priorReview && priorReview.issues) || []).filter(i => i && isIssueBlocking('final_review', 'medium', i.severity, i.blocking))
  const targetedFix = {
    prior_blocking_issue_ids: priorBlocking.map(i => i.id || i.prior_issue_id || '').filter(Boolean),
    fix_result: {
      fixed_issue_ids: finalImpl.fixed_issue_ids || [],
      targeted_verification: finalImpl.targeted_verification || [],
      verification_failures: finalImpl.verification_failures || [],
      unrelated_files_changed: finalImpl.unrelated_files_changed || [],
      diff_summary: finalImpl.diff_summary || '',
      scope_justifications: finalImpl.scope_justifications || [],
    },
    final_fix_diff_evidence: latestDiffEvidence(finalImpl, finalTask) || null,
    prior_review: priorReview || null,
  }
  return `Final cross-task review after all tasks passed.

## Completed Tasks

${JSON.stringify(completedSummary, null, 2)}

## Branch Diff Evidence

${JSON.stringify(branchDiffEvidence, null, 2)}

Inspect branch-level diff evidence first. Prefer controller metadata for changed files. Expected commands are git diff --name-status BASE...HEAD and git diff BASE...HEAD, or explicit BASE_SHA..HEAD when applicable.

Review only cross-task integration bugs, conflicts, duplicated changes, missing shared tests, regression risk, and branch-wide consistency issues.
Do not propose or apply final fixes. Report blocking findings only as review issues.

## Final Targeted Re-Review Requirements

${priorReview ? JSON.stringify(targetedFix, null, 2) : 'Initial review; no prior findings.'}

If this is a final re-review:
- Cover the full branch diff plus the final fix diff evidence.
- Verify every prior blocking issue by ID in prior_findings_verified[].
- Put repeated unresolved issues in unresolved_issue_ids and preserve prior_issue_id on carried-forward findings.
- Report new_issues separately from repeated unresolved issues.
- Set diff_verified from controller branch and final fix diff/base metadata, not agent claims.
- Set targeted_verification_credible only if targeted commands cover fixed_issue_ids.
- Include scope_concerns for final fixes outside review issue files or stale task evidence.

Blocking severities: Critical, High, Important. Minor/Info are non-blocking.
If any blocking issue exists, passed must be false even if an optimistic pass seems tempting.
Require issue file/line where available; if omitted, include location_unavailable_reason.

## Structured Output

Your final response will be parsed as JSON. You MUST return valid JSON.` + diffAnchorPrompt(finalTask, finalImpl, 'final')
}

function specReviewPrompt(task, impl, priorReview) {
  const concerns = (impl.concerns || []).join('\n') || 'None reported'
  const evidenceValidation = impl.evidence_validation ? JSON.stringify(impl.evidence_validation, null, 2) : 'Not provided'
  const acceptanceCoverage = JSON.stringify(impl.acceptance_coverage || [], null, 2)
  const unverifiedRefs = (impl.unverified_acceptance_refs || []).join('\n') || 'None reported'
  const limitations = (impl.limitations || (impl.evidence_validation && impl.evidence_validation.limitations) || []).join('\n') || 'None reported'
  const priorBlocking = ((priorReview && priorReview.issues) || []).filter(i => i && (i.blocking || i.severity === 'Critical' || i.severity === 'High' || i.severity === 'Important'))
  const targetedFix = {
    prior_blocking_issue_ids: priorBlocking.map(i => i.id || i.prior_issue_id || '').filter(Boolean),
    fix_result: {
      fixed_issue_ids: impl.fixed_issue_ids || [],
      targeted_verification: impl.targeted_verification || [],
      verification_failures: impl.verification_failures || [],
      unrelated_files_changed: impl.unrelated_files_changed || [],
      diff_summary: impl.diff_summary || '',
      scope_justifications: impl.scope_justifications || [],
    },
    controller_detected_unrelated_files: validateLatestFixScope(task, priorBlocking, impl, task).reasons || [],
    prior_review: priorReview || null,
  }
  return `Verify whether the implementation matches its specification.

## What Was Requested

${task.description}

## What The Implementer Claims

${impl.summary}

Reported files changed (untrusted unless diff evidence confirms): ${impl.files_modified.join(', ')}

## Implementation Evidence

Acceptance coverage:
${acceptanceCoverage}

Stale/unverified refs:
${unverifiedRefs}

Review requirements and acceptance only. Use actual code diff and implementation evidence. Include stale/unverified refs as limitations. Avoid style, general code quality, or broader design review scope.

## Implementation Concerns / Limitations

Concerns:
${concerns}

Evidence validation:
${evidenceValidation}

Limitations:
${limitations}

## Targeted Re-Review Requirements

${priorReview ? JSON.stringify(targetedFix, null, 2) : 'Initial review; no prior findings.'}

If this is a re-review:
- Verify every prior blocking issue by ID in prior_findings_verified[].
- Put repeated unresolved issues in unresolved_issue_ids and preserve prior_issue_id on carried-forward findings.
- Report new_issues separately from repeated unresolved issues.
- Set diff_verified from controller diff/base metadata, not agent claims.
- Set targeted_verification_credible only if targeted commands cover fixed_issue_ids.
- Include scope_concerns for controller-detected unrelated files and unexplained scope expansion.

## CRITICAL: Do Not Trust the Report

The implementer may have finished suspiciously quickly. Their report may be
incomplete, inaccurate, or optimistic. You MUST verify everything independently.

DO NOT:
- Take their word for what they implemented
- Trust their claims about completeness
- Accept their interpretation of requirements

DO:
- Inspect controller diff evidence first
- Read the actual code shown by the diff
- Compare actual implementation to requirements line by line
- Check for missing pieces they claimed to implement
- Look for extra features they didn't mention
- Preserve role boundaries; do not duplicate later code-quality findings unless they show unresolved spec noncompliance
- Require issue file/line where available; if omitted, include location_unavailable_reason
- Preserve prior_issue_id when carrying forward unresolved findings

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

Your final response will be parsed as JSON. You MUST return valid JSON.` + diffEvidencePrompt(task, impl, 'spec_review')
}

function codeReviewPrompt(impl, taskId, task, priorReview) {
  const priorBlocking = ((priorReview && priorReview.issues) || []).filter(i => i && (i.blocking || i.severity === 'Critical' || i.severity === 'High' || i.severity === 'Important'))
  const targetedFix = {
    prior_blocking_issue_ids: priorBlocking.map(i => i.id || i.prior_issue_id || '').filter(Boolean),
    fix_result: {
      fixed_issue_ids: impl.fixed_issue_ids || [],
      targeted_verification: impl.targeted_verification || [],
      verification_failures: impl.verification_failures || [],
      unrelated_files_changed: impl.unrelated_files_changed || [],
      diff_summary: impl.diff_summary || '',
      scope_justifications: impl.scope_justifications || [],
    },
    controller_detected_unrelated_files: validateLatestFixScope(task || {}, priorBlocking, impl, task || {}).reasons || [],
    prior_review: priorReview || null,
  }
  return `Review the implementation for code quality.

## Context

Task: ${taskId}
Summary: ${impl.summary}
Reported files (untrusted unless controller diff confirms): ${impl.files_modified.join(', ')}

## Targeted Re-Review Requirements

${priorReview ? JSON.stringify(targetedFix, null, 2) : 'Initial review; no prior findings.'}

If this is a re-review:
- Verify every prior blocking issue by ID in prior_findings_verified[].
- Put repeated unresolved issues in unresolved_issue_ids and preserve prior_issue_id on carried-forward findings.
- Report new_issues separately from repeated unresolved issues.
- Set diff_verified from controller diff/base metadata, not agent claims.
- Set targeted_verification_credible only if targeted commands cover fixed_issue_ids.
- Include scope_concerns for controller-detected unrelated files and unexplained scope expansion.

## Instructions

Inspect controller diff metadata first. Treat files_modified as untrusted. If diff_verified=false, say so and include the limitation. Do not run conflicting scope unless needed to resolve unclear diff evidence.

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
Preserve role boundaries. Do not duplicate prior spec/code findings unless unresolved.
Require issue file/line where available; if omitted, include location_unavailable_reason.
Preserve prior_issue_id when carrying forward unresolved findings.

## Severity

Critical: would cause a bug, break the build, or violate a core requirement.
Important: maintainability problems that should be addressed.
Minor: style nits.

## Structured Output

Your final response will be parsed as JSON. You MUST return valid JSON.` + diffEvidencePrompt(task || { id: taskId }, impl, taskId === 'final' ? 'final_review' : 'code_review')
}

function fixPrompt(issues, files, task, impl, stage, retryCount) {
  const issueList = Array.isArray(issues) ? issues : []
  const issuesText = typeof issues === 'string' ? issues : JSON.stringify(issues, null, 2)
  const allowedFiles = (files || []).filter(Boolean)
  const context = {
    stage: stage || 'fix',
    task: task && { id: task.id, description: task.description },
    prior_blocking_issue_ids: issueList.map(i => i && (i.id || i.prior_issue_id)).filter(Boolean),
    allowed_files: allowedFiles,
    controller_diff_base_metadata: {
      diff_anchor: resolveDiffAnchors(typeof args === 'undefined' ? {} : args, task || {}, impl || {}, stage || 'fix'),
      latest_diff_evidence: latestDiffEvidence(impl, task) || collectDiffEvidence(resolveDiffAnchors(typeof args === 'undefined' ? {} : args, task || {}, impl || {}, stage || 'fix')),
    },
    prior_evidence: {
      summary: impl && impl.summary,
      files_modified: impl && impl.files_modified,
      verification_results: impl && impl.verification_results,
      acceptance_coverage: impl && impl.acceptance_coverage,
      diff_summary: impl && impl.diff_summary,
    },
    required_commands_acceptance_refs: {
      required_commands: (task && task.required_commands) || [],
      acceptance_refs: (task && task.acceptance_refs) || [],
      verification: (task && task.verification) || [],
      tests: (task && task.tests) || [],
    },
    retry_count: retryCount || 0,
  }
  return `Fix the following review issues in the implementation.

## Targeted Fix Context

Stage: ${context.stage}
Task: ${context.task && context.task.id || 'unknown'}
Retry count: ${context.retry_count}
Prior blocking issue IDs: ${context.prior_blocking_issue_ids.join(', ') || 'none'}
Allowed files: ${allowedFiles.join(', ') || 'none'}

Controller diff/base metadata:
${JSON.stringify(context.controller_diff_base_metadata, null, 2)}

Prior evidence:
${JSON.stringify(context.prior_evidence, null, 2)}

Required commands / acceptance refs:
${JSON.stringify(context.required_commands_acceptance_refs, null, 2)}

## Issues to Fix

${issuesText}

## Files to Modify

${allowedFiles.join(', ')}

## Instructions

1. Read each file listed above
2. Fix only the listed prior blocking issue IDs
3. Do NOT make changes beyond fixing these specific issues
4. Do NOT refactor, restructure, or "improve" unrelated code
5. Run targeted verification for each fixed issue ID plus required commands
6. Commit with: fix(review): address review findings

## Structured Output

For DONE/DONE_WITH_CONCERNS include the normal implementation fields plus fixed_issue_ids, targeted_verification, verification_failures, unrelated_files_changed, diff_summary, scope_justifications.
Your final response will be parsed as JSON. You MUST return valid JSON.` + diffAnchorPrompt(task || {}, impl || {}, stage || 'fix')
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

function normalizeReviewResult(review, stage, taskId, priorReview) {
  if (!review) return review
  return normalizeReviewIssues(review, {
    stage,
    task_id: taskId || (stage === 'final_review' ? 'final' : 'unknown'),
    prior_issues: (priorReview && priorReview.issues) || [],
  })
}

function hasBlockingRereviewMetadata(review) {
  if (!review) return false
  const verified = Array.isArray(review.prior_findings_verified) ? review.prior_findings_verified : []
  const verifiedIds = new Set(verified.filter(finding => finding && finding.verified === true).map(finding => finding.id || finding.issue_id || finding.prior_issue_id).filter(Boolean))
  const priorIds = Array.isArray(review._prior_blocking_issue_ids) ? review._prior_blocking_issue_ids : []
  return (Array.isArray(review.unresolved_issue_ids) && review.unresolved_issue_ids.length > 0) ||
    verified.some(finding => finding && finding.verified === false) ||
    priorIds.some(id => !verifiedIds.has(id)) ||
    review.targeted_verification_credible === false ||
    review.diff_verified === false ||
    (Array.isArray(review.scope_concerns) && review.scope_concerns.length > 0)
}

function unresolvedIssueIds(review) {
  return review && Array.isArray(review.unresolved_issue_ids) ? review.unresolved_issue_ids : []
}

function taskFilesForFinalStaleness(entry) {
  return (entry && (entry.files || (entry.evidence && entry.evidence.files_modified) || []) || []).map(normalizePathForScope).filter(Boolean)
}

function collectFinalFixTouchedFiles(finalTask) {
  const latest = ((finalTask && finalTask.attempt_diff_evidence) || []).slice(-1)[0] || {}
  const fromDiff = latest.diff_files || []
  const fromStatus = [latest.committed_diff, latest.worktree_diff]
    .filter(Boolean)
    .flatMap(section => section.files || [])
  return [...new Set([...fromDiff, ...fromStatus].map(normalizePathForScope).filter(Boolean))]
}

function tasksStaleAfterFinalFix(completed, touchedFiles) {
  const touched = new Set((touchedFiles || []).map(normalizePathForScope).filter(Boolean))
  if (touched.size === 0) return []
  const stale = []
  for (const entry of completed || []) {
    const files = taskFilesForFinalStaleness(entry).filter(file => touched.has(file))
    if (files.length > 0) stale.push({ task_id: entry.id, files, reason: 'final_fix_touched_completed_task_files' })
  }
  return stale
}

function mergeTasksStaleAfterFinalFix(existing, next) {
  const merged = new Map()
  for (const item of [...(existing || []), ...(next || [])]) {
    if (!item || !item.task_id) continue
    const current = merged.get(item.task_id) || { task_id: item.task_id, files: [], reason: 'final_fix_touched_completed_task_files' }
    current.files = [...new Set([...current.files, ...(item.files || [])].map(normalizePathForScope).filter(Boolean))]
    merged.set(item.task_id, current)
  }
  return [...merged.values()]
}

function finalFixInvalidatesTaskEvidence(completed, staleTasks) {
  const staleIds = new Set((staleTasks || []).map(item => item && item.task_id).filter(Boolean))
  return (completed || []).some(entry => staleIds.has(entry.id) && (!entry.evidence_validation || entry.evidence_validation.status !== 'pass'))
}

function normalizeFinalReview(review, branchDiffEvidence) {
  const normalized = normalizeReviewResult(review, 'final_review', 'final', null) || { passed: false, issues: [], summary: 'Final review returned invalid output' }
  const blockingIssues = (normalized.issues || []).filter(issue => isIssueBlocking('final_review', 'medium', issue.severity, issue.blocking))
  const unresolved = [...new Set([...(normalized.unresolved_issue_ids || []), ...blockingIssues.map(issue => issue.id).filter(Boolean)])]
  return {
    ...normalized,
    passed: blockingIssues.length === 0 && normalized.passed === true,
    unresolved_issue_ids: unresolved,
    branch_diff_evidence: branchDiffEvidence,
  }
}

function reviewOverrideDecisionAllowsConcerns(impl, codeReview) {
  if (!impl || impl.status !== 'DONE_WITH_CONCERNS') return true
  return !!(codeReview && codeReview.passed === true && !hasBlockingIssues(codeReview, 'code_review', 'medium'))
}

// ── Extract evidence from impl result ─────────────────────────────────

function normalizeRuntimeEvidenceRequirement(task) {
  const value = task && task.runtime_evidence_required
  if (value === true) return 'command'
  if (value === 'required') return 'artifact'
  if (value === 'artifact' || value === 'command') return value
  return 'none'
}

function plannedVerification(task) {
  return [
    ...((task && task.tests) || []),
    ...((task && task.verification) || []),
  ]
}

function extractEvidence(task, impl, controllerEvidence, codeReview) {
  const reviews = [controllerEvidence, codeReview].filter(Boolean)
  const controllerCommands = reviews.flatMap(r => r.command_results || [])
  const controllerPromptOnly = controllerCommands.length === 0 && reviews.every(r => r.prompt_only || !r.command_results)
  const agentCommands = (impl && impl.verification_results) || []
  const controllerDiffEvidence = reviews.flatMap(r => r.diff_evidence || r.controller_diff_evidence || [])
  const verifiedDiffEvidence = controllerDiffEvidence.filter(e => e && e.diff_verified)
  const diffSummary = (impl && impl.diff_summary) || verifiedDiffEvidence.flatMap(e => e.diff_files || []).join(', ')
  return {
    base_sha: (impl && impl.base_sha) || (verifiedDiffEvidence[0] && verifiedDiffEvidence[0].base_sha) || '',
    head_sha: (impl && impl.head_sha) || (verifiedDiffEvidence[0] && verifiedDiffEvidence[0].head_sha) || '',
    commit_sha: (impl && (impl.commit_sha || impl.dirty_commit_sha)) || '',
    test_results: (impl && impl.test_results) || '',
    verification_commands: (impl && impl.verification_commands) || [],
    planned_verification: plannedVerification(task),
    executed_commands: controllerCommands.length > 0 || !controllerPromptOnly ? controllerCommands : agentCommands,
    evidence_paths: reviews.flatMap(r => r.evidence_paths || []).concat((impl && impl.evidence_paths) || []),
    concerns: (impl && impl.concerns) || [],
    acceptance_coverage: (impl && impl.acceptance_coverage) || [],
    unverified_acceptance_refs: (impl && impl.unverified_acceptance_refs) || [],
    diff_summary: diffSummary,
    controller_diff_evidence: controllerDiffEvidence,
    files_modified: (impl && impl.files_modified) || [],
    runtime_evidence_required: normalizeRuntimeEvidenceRequirement(task),
  }
}

function commandMatches(required, actual, substitutes) {
  const allowed = [required, ...((substitutes && substitutes[required]) || [])]
  return allowed.some(prefix => actual === prefix || actual.indexOf(prefix + ' ') === 0)
}

function evidencePathExists(path, pathExists) {
  if (pathExists && Object.prototype.hasOwnProperty.call(pathExists, path)) return pathExists[path]
  return true
}

function controllerEvidenceFromAttempts(ctx) {
  const attempts = (ctx && ctx.attempt_diff_evidence) || []
  const verified = attempts.filter(e => e && e.diff_verified)
  return {
    prompt_only: verified.length === 0 && attempts.every(e => !(e.command_results || []).length && !(e.evidence_paths || []).length),
    diff_evidence: attempts,
    command_results: attempts.flatMap(e => e.command_results || []),
    evidence_paths: attempts.flatMap(e => e.evidence_paths || []),
    path_exists: attempts.reduce((acc, e) => ({ ...acc, ...((e && e.path_exists) || {}) }), {}),
  }
}

function implementationEvidenceCleanPass(evidence) {
  return evidence && evidence.status === 'pass'
}

function normalizePathForScope(path) {
  return String(path || '').replace(/\\/g, '/').replace(/^\.\//, '')
}

function dirnameForScope(path) {
  const normalized = normalizePathForScope(path)
  const index = normalized.lastIndexOf('/')
  return index === -1 ? '' : normalized.slice(0, index)
}

function basenameForScope(path) {
  const normalized = normalizePathForScope(path)
  const index = normalized.lastIndexOf('/')
  return index === -1 ? normalized : normalized.slice(index + 1)
}

function isTestPath(path) {
  const normalized = normalizePathForScope(path).toLowerCase()
  const base = basenameForScope(normalized)
  return normalized.includes('/test/') || normalized.includes('/tests/') || normalized.startsWith('test/') || normalized.startsWith('tests/') ||
    base.startsWith('test_') || base.endsWith('.test.js') || base.endsWith('.test.ts') || base.endsWith('.spec.js') || base.endsWith('.spec.ts') || base.endsWith('_test.py')
}

function isSameDirectoryTestPattern(file, allowedFiles) {
  if (!isTestPath(file)) return false
  const dir = dirnameForScope(file)
  const base = basenameForScope(file).toLowerCase()
  return allowedFiles.some(allowed => {
    const allowedDir = dirnameForScope(allowed)
    const stem = basenameForScope(allowed).replace(/\.[^.]+$/, '').toLowerCase()
    return dir === allowedDir && (base.includes(stem) || base.includes(stem.replace(/^test[_-]/, '')))
  })
}

function isBroadConfigFile(file) {
  const normalized = normalizePathForScope(file).toLowerCase()
  const base = basenameForScope(normalized)
  if (normalized.startsWith('.github/workflows/')) return true
  if (['package.json', 'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'bun.lockb', 'requirements.txt', 'pyproject.toml', 'poetry.lock', 'cargo.toml', 'cargo.lock', 'go.mod', 'go.sum', 'webpack.config.js', 'vite.config.js', 'rollup.config.js', 'tsconfig.json', 'dockerfile', 'makefile'].includes(base)) return true
  if (/^dockerfile[.-]/.test(base)) return true
  if (/^(jenkinsfile|circle\.yml|azure-pipelines\.ya?ml|bitbucket-pipelines\.ya?ml|cloudbuild\.ya?ml)$/.test(base)) return true
  if (/^(babel|eslint|prettier|postcss|tailwind|jest|vitest|rollup|webpack|vite|tsup|esbuild)\.config\.[cm]?[jt]s$/.test(base)) return true
  if (/^\.(babelrc|eslintrc|prettierrc)(\.|$)/.test(base)) return true
  return false
}

function addAllowedPath(set, path) {
  const normalized = normalizePathForScope(path)
  if (normalized) set.add(normalized)
}

function collectIssueFiles(issues) {
  return (issues || []).map(issue => {
    const explicit = issue && (issue.file || issue.path)
    if (explicit) return normalizePathForScope(explicit)
    const location = String((issue && issue.location) || '').trim()
    const match = location.match(/^(.+?)(?::\d+(?::\d+)?)?$/)
    return normalizePathForScope(match && match[1])
  }).filter(Boolean)
}

function parseFixScopeDiffFiles(diffFiles) {
  const changed = []
  const deleted = []
  const renamed = []
  for (const entry of diffFiles || []) {
    const line = typeof entry === 'string' ? entry : ''
    const parts = line.split('\t')
    const status = parts[0] || ''
    if (parts.length > 1 && /^[A-Z-]/.test(status)) {
      if (status[0] === 'D') deleted.push(parts[1] || '')
      if (status[0] === 'R') renamed.push({ from: parts[1] || '', to: parts[2] || '', status })
      for (const file of nameStatusFiles(line)) changed.push(file)
    } else {
      changed.push(line)
    }
  }
  return {
    changed: changed.map(normalizePathForScope).filter(Boolean),
    deleted: deleted.map(normalizePathForScope).filter(Boolean),
    renamed,
  }
}

function stripScopeExtension(path) {
  return normalizePathForScope(path).replace(/\.[^.\/]+$/, '')
}

function resolveRelativeImportForScope(fromFile, specifier) {
  const spec = String(specifier || '').trim()
  if (!spec.startsWith('.')) return ''
  const base = dirnameForScope(fromFile)
  const parts = (base ? base.split('/') : []).concat(spec.split('/'))
  const resolved = []
  for (const part of parts) {
    if (!part || part === '.') continue
    if (part === '..') resolved.pop()
    else resolved.push(part)
  }
  return stripScopeExtension(resolved.join('/'))
}

function importSpecifiersFromLine(line) {
  const text = String(line || '')
  const specs = []
  const importMatch = text.match(/\bimport\s+(?:[^'"()]+?\s+from\s+)?['"]([^'"]+)['"]/) || text.match(/\bexport\s+[^'"()]+?\s+from\s+['"]([^'"]+)['"]/) || text.match(/\bimport\s*\(\s*['"]([^'"]+)['"]\s*\)/)
  const requireMatch = text.match(/\brequire\s*\(\s*['"]([^'"]+)['"]\s*\)/)
  if (importMatch) specs.push(importMatch[1])
  if (requireMatch) specs.push(requireMatch[1])
  return specs
}

function collectActualImportSupport(diffEvidence, allowedFiles) {
  const allowedStems = new Set(Array.from(allowedFiles || []).map(stripScopeExtension))
  const support = []
  for (const evidence of diffEvidence || []) {
    for (const section of [evidence && evidence.committed_diff, evidence && evidence.worktree_diff]) {
      let current = ''
      for (const line of String((section && section.diff_body) || '').split('\n')) {
        const header = line.match(/^\+\+\+ b\/(.+)$/)
        if (header) current = normalizePathForScope(header[1])
        if (!current || !allowedStems.has(stripScopeExtension(current)) || !line.startsWith('+') || line.startsWith('+++')) continue
        for (const spec of importSpecifiersFromLine(line.slice(1))) addAllowedPath({ add: value => support.push(value) }, resolveRelativeImportForScope(current, spec))
      }
    }
  }
  return support
}

function validateFixScope(diffFiles, allowedFiles, fixResult) {
  const result = fixResult || {}
  const task = result.task || {}
  const issues = result.issues || (Array.isArray(allowedFiles) && allowedFiles.some(item => item && typeof item === 'object') ? allowedFiles : [])
  const explicitAllowed = Array.isArray(allowedFiles) && allowedFiles.every(item => typeof item === 'string') ? allowedFiles : []
  const allowed = new Set()
  for (const file of explicitAllowed) addAllowedPath(allowed, file)
  for (const file of collectIssueFiles(issues)) addAllowedPath(allowed, file)
  for (const file of task.pre_fix_changed_files || task.preFixChangedFiles || []) addAllowedPath(allowed, file)
  for (const file of task.files || []) addAllowedPath(allowed, file)
  for (const file of task.tests || []) addAllowedPath(allowed, file)

  const support = result.support || task.support || {}
  const imports = support.imports || support.imported_by_allowed_files || support.justified_imports || {}
  for (const file of Array.from(allowed)) {
    for (const imported of imports[file] || imports[normalizePathForScope(file)] || []) addAllowedPath(allowed, imported)
  }
  for (const imported of collectActualImportSupport(result.diff_evidence || result.controller_diff_evidence || task.attempt_diff_evidence || [], allowed)) addAllowedPath(allowed, imported)

  const parsed = parseFixScopeDiffFiles(diffFiles || [])
  const changed = parsed.changed
  const formattingOnly = new Set((result.formatting_only_files || result.formattingOnlyFiles || []).map(normalizePathForScope))
  const deleted = [
    ...parsed.deleted,
    ...(result.deleted_files || result.deletedFiles || []).map(normalizePathForScope),
  ]
  const renamed = [
    ...parsed.renamed,
    ...(result.renamed_files || result.renamedFiles || []),
  ]
  const reasons = []

  const allowedStems = new Set(Array.from(allowed).map(stripScopeExtension))
  for (const file of changed) {
    const scoped = allowed.has(file) || allowedStems.has(stripScopeExtension(file)) || isSameDirectoryTestPattern(file, Array.from(allowed))
    if (isBroadConfigFile(file)) reasons.push('broad_config_change: ' + file)
    else if (!scoped) reasons.push(formattingOnly.has(file) ? 'formatting_only_outside_scope: ' + file : 'unrelated_file_changed: ' + file)
  }
  for (const file of deleted) reasons.push('delete_outside_fix_scope: ' + file)
  for (const entry of renamed) {
    const from = normalizePathForScope(entry && (entry.from || entry.old || entry[0]))
    const to = normalizePathForScope(entry && (entry.to || entry.new || entry[1]))
    reasons.push('rename_outside_fix_scope: ' + from + ' -> ' + to)
  }

  return {
    passed: reasons.length === 0,
    status: reasons.length === 0 ? 'pass' : 'block',
    reasons,
    allowed_files: Array.from(allowed),
    diff_files: changed,
    advisory: { unrelated_files_changed: result.unrelated_files_changed || [] },
  }
}

function validateLatestFixScope(ctx, issues, updated, task) {
  const latest = ((ctx && ctx.attempt_diff_evidence) || []).slice(-1)[0] || {}
  return validateFixScope(latest.diff_files || [], issues, {
    ...(updated || {}),
    task: task || ctx || {},
    issues,
    deleted_files: latest.special_statuses && latest.special_statuses.deleted,
    renamed_files: latest.special_statuses && latest.special_statuses.renamed,
  })
}

function fixIssueFiles(issues) {
  return collectIssueFiles(issues || [])
}

function collectIssueIdAliases(item) {
  const ids = []
  if (!item) return ids
  if (Array.isArray(item.issue_ids)) ids.push(...item.issue_ids)
  for (const field of ['issue_id', 'id', 'prior_issue_id']) {
    if (item[field]) ids.push(item[field])
  }
  return ids
}

function validateFixResultContract(updated, priorIssues) {
  const reasons = []
  if (!updated) reasons.push('missing_fix_result')
  if (updated && (updated.status === 'DONE' || updated.status === 'DONE_WITH_CONCERNS')) {
    for (const field of ['fixed_issue_ids', 'targeted_verification', 'verification_failures', 'unrelated_files_changed', 'scope_justifications']) {
      if (!Array.isArray(updated[field])) reasons.push('missing_' + field)
    }
    const priorIds = (priorIssues || []).map(issue => issue && issue.id).filter(Boolean)
    const fixedIds = new Set(Array.isArray(updated.fixed_issue_ids) ? updated.fixed_issue_ids : [])
    const targetedIds = new Set((Array.isArray(updated.targeted_verification) ? updated.targeted_verification : []).flatMap(collectIssueIdAliases))
    for (const id of priorIds) {
      if (!fixedIds.has(id)) reasons.push('missing_fixed_issue_id: ' + id)
      if (!targetedIds.has(id)) reasons.push('missing_targeted_verification: ' + id)
    }
    for (const id of Array.from(fixedIds)) {
      if (!targetedIds.has(id)) reasons.push('missing_targeted_verification: ' + id)
    }
    for (const failure of Array.isArray(updated.verification_failures) ? updated.verification_failures : []) {
      reasons.push('verification_failure: ' + (failure && (failure.issue_id || failure.id || failure.command || failure.reason) || 'unknown'))
    }
  }
  return { passed: reasons.length === 0, status: reasons.length === 0 ? 'pass' : 'block', reasons }
}

function validateImplementationEvidence(task, impl, controllerEvidence, reviewOverride) {
  const evidence = extractEvidence(task, impl, controllerEvidence, reviewOverride)
  const reasons = []
  const commands = evidence.executed_commands || []
  const required = (task && task.required_commands) || []
  const substitutes = (task && task.command_substitutes) || {}
  const expectedNonzero = (task && task.expected_nonzero_commands) || []

  if (!impl) reasons.push('missing_implementation_result')
  if (impl && impl.status === 'BLOCKED') reasons.push('implementation_blocked: ' + (impl.blocker_detail || 'BLOCKED'))
  if (impl && (impl.status === 'DONE' || impl.status === 'DONE_WITH_CONCERNS')) {
    if (!evidence.test_results) reasons.push('missing_test_results')
    if (!Array.isArray(evidence.verification_commands) || evidence.verification_commands.length === 0) reasons.push('missing_verification_commands')
    if (!Array.isArray(impl.verification_results) || impl.verification_results.length === 0) reasons.push('missing_verification_results')
    if (!evidence.base_sha) reasons.push('missing_base_sha')
    if (!evidence.head_sha) reasons.push('missing_head_sha')
    if (!Array.isArray(evidence.acceptance_coverage) || evidence.acceptance_coverage.length === 0) reasons.push('missing_acceptance_coverage')
    if (!Object.prototype.hasOwnProperty.call(impl, 'unverified_acceptance_refs') || !Array.isArray(impl.unverified_acceptance_refs)) reasons.push('missing_unverified_acceptance_refs')
    if (!Object.prototype.hasOwnProperty.call(impl, 'concerns') || !Array.isArray(impl.concerns)) reasons.push('missing_concerns')
    if (!evidence.diff_summary) reasons.push('missing_diff_summary')
  }
  if (impl && impl.status === 'DONE' && evidence.concerns.length > 0) reasons.push('done_has_concerns')
  if (impl && impl.status === 'DONE_WITH_CONCERNS' && evidence.concerns.length === 0) reasons.push('missing_concerns')

  for (const command of required) {
    if (!commands.some(result => {
      const actual = result.command || ''
      const expected = expectedNonzero.some(prefix => commandMatches(prefix, actual, {}))
      return commandMatches(command, actual, substitutes) && (result.exit_code === 0 || expected)
    })) {
      reasons.push('missing_required_command: ' + command)
    }
  }

  for (const result of commands) {
    const command = result.command || ''
    const expected = expectedNonzero.some(prefix => commandMatches(prefix, command, {}))
    if (result.exit_code !== 0 && !expected) reasons.push('command_failed: ' + command)
  }

  if (evidence.runtime_evidence_required === 'command' && commands.length === 0) reasons.push('missing_runtime_command_evidence')
  if (evidence.runtime_evidence_required === 'artifact' && evidence.evidence_paths.length === 0) {
    reasons.push('missing_evidence_artifact')
  }
  for (const path of evidence.evidence_paths) {
    if (!evidencePathExists(path, controllerEvidence && controllerEvidence.path_exists)) reasons.push('evidence_path_missing: ' + path)
  }

  const refs = ((reviewOverride && reviewOverride.acceptance_refs) || (task && task.acceptance_refs) || [])
  const concernText = ((impl && impl.concerns) || []).join('\n')
  if (impl && impl.status === 'DONE_WITH_CONCERNS') {
    for (const ref of refs) {
      if (concernText.indexOf(ref) === -1) reasons.push('missing_acceptance_concern: ' + ref)
    }
  }

  const limitations = []
  const promptOnly = [controllerEvidence, reviewOverride].filter(Boolean).some(r => r.prompt_only)
  if (promptOnly) limitations.push('prompt_only_evidence_unverified')
  if (evidence.unverified_acceptance_refs.length > 0) limitations.push('unverified_acceptance_refs: ' + evidence.unverified_acceptance_refs.join(', '))

  let status = 'pass'
  if (reasons.length > 0) status = 'block'
  else if (evidence.unverified_acceptance_refs.length > 0) status = 'prompt_only_unverified'
  else if (impl && impl.status === 'DONE_WITH_CONCERNS' && promptOnly) status = 'needs_review_override'

  return { passed: reasons.length === 0, status, reasons, limitations, evidence }
}

// ── Result adapter: classify task into exactly one partition ──────────

function classifyTaskResult(taskId, task, ctx) {
  const attemptBase = {
    task_attempt_base_sha: ctx.task_attempt_base_sha || task.task_attempt_base_sha || '',
    task_attempt_base_dirty: !!(ctx.task_attempt_base_dirty || task.task_attempt_base_dirty),
    task_attempt_base_capture_failed: ctx.task_attempt_base_capture_failed || task.task_attempt_base_capture_failed || '',
    spec_fix_attempts: ctx.spec_fix_attempts || 0,
    code_fix_attempts: ctx.code_fix_attempts || 0,
  }

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
        evidence: ctx.evidence_validation && ctx.evidence_validation.evidence,
        evidence_validation: ctx.evidence_validation,
        ...attemptBase,
        attempt_diff_evidence: ctx.attempt_diff_evidence || [],
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
        ...attemptBase,
        attempt_diff_evidence: ctx.attempt_diff_evidence || [],
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
        unresolved_issue_ids: unresolvedIssueIds(ctx.spec_review),
        spec_passed: false,
        code_passed: false,
        iterations: ctx._iterations_spec || 0,
        evidence: extractEvidence(task, ctx.impl, ctx.spec_review, null),
        evidence_validation: ctx.evidence_validation,
        ...attemptBase,
        attempt_diff_evidence: ctx.attempt_diff_evidence || [],
      },
    }
  }

  const implementationEvidence = ctx.evidence_validation || validateImplementationEvidence(task, ctx.impl, ctx.implementation_evidence, ctx.code_review)

  if (!implementationEvidence.passed) {
    return {
      partition: 'blocked',
      entry: {
        id: taskId,
        reason: implementationEvidence.reasons.join('; '),
        classification: 'runtime_failure',
        impl: ctx.impl,
        evidence: implementationEvidence.evidence,
        evidence_validation: implementationEvidence,
        ...attemptBase,
        attempt_diff_evidence: ctx.attempt_diff_evidence || [],
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
        unresolved_issue_ids: unresolvedIssueIds(ctx.code_review),
        spec_passed: true,
        code_passed: false,
        iterations: ctx._iterations_code || 0,
        evidence: extractEvidence(task, ctx.impl, ctx.spec_review, ctx.code_review),
        evidence_validation: ctx.evidence_validation,
        ...attemptBase,
        attempt_diff_evidence: ctx.attempt_diff_evidence || [],
      },
    }
  }

  if (!reviewOverrideDecisionAllowsConcerns(ctx.impl, ctx.code_review)) {
    return {
      partition: 'blocked',
      entry: {
        id: taskId,
        reason: 'DONE_WITH_CONCERNS requires passed code review override',
        classification: 'runtime_failure',
        impl: ctx.impl,
        evidence: implementationEvidence.evidence,
        evidence_validation: {
          ...implementationEvidence,
          passed: false,
          status: 'block',
          reasons: [...(implementationEvidence.reasons || []), 'missing_review_override_for_concerns'],
        },
        ...attemptBase,
        attempt_diff_evidence: ctx.attempt_diff_evidence || [],
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
        ...attemptBase,
        attempt_diff_evidence: ctx.attempt_diff_evidence || [],
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
      evidence: implementationEvidence.evidence,
      evidence_validation: implementationEvidence,
      implementation_evidence: ctx.implementation_evidence,
      files: (ctx.impl && ctx.impl.files_modified) || [],
      ...attemptBase,
      attempt_diff_evidence: ctx.attempt_diff_evidence || [],
    },
  }
}

// ── Phase 1: Scope ───────────────────────────────────────────────────
// Resume: if scope already completed, skip entirely.

if (shouldSkipPhase('scope')) {
  log('Phase: Scope — SKIPPED (resume)')
  auditEvents.push({ phase: 'scope', event: 'phase_skipped', reason: 'resume' })
} else {
phase('Scope')
await flowState('event', { type: 'phase_start', phase: 'scope' })
scope = await agent(
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
await flowState('update', { phase: 'scope', progress: { tasks_total: 0 } })
auditEvents.push({ phase: 'scope', event: 'phase_complete', angles: scope.angles.length })
} // end scope skip guard

// ── Phase 2: Research ────────────────────────────────────────────────
// Resume: if research already completed, skip entirely.

if (shouldSkipPhase('research')) {
  log('Phase: Research — SKIPPED (resume)')
  auditEvents.push({ phase: 'research', event: 'phase_skipped', reason: 'resume' })
} else {
phase('Research')
await flowState('event', { type: 'phase_start', phase: 'research' })
const researchResults = await parallel(
  scope.angles.map(angle => () =>
    agent(
      `Research this angle for the task. Search the codebase first. Use web search or web fetch when the angle depends on current external information, recent library/API behavior, docs, ecosystem conventions, or URLs discovered during research.

## Task

${task}

## Strategy

${scope.strategy}

## Your Angle: ${angle.key}

${angle.question}

## Web Research Guidance

- Use web search for recent information, official docs, release notes, issues, or ecosystem examples when local code is insufficient.
- Use web fetch to read specific URLs surfaced by search results, existing docs, or the task context.
- Prefer official/primary sources. Include URLs for external claims.
- Do not use web tools for secrets, private/internal URLs, or questions fully answerable from the codebase.

Produce detailed findings with file paths, line numbers, or URLs.
3-5 key insights. Note open questions. Be thorough — your findings
feed directly into the specification.`,
      agentOpts(`research:${angle.key}`, 'Research', RESEARCH_SCHEMA),
    ),
  ),
)

allFindings = researchResults.filter(Boolean)
log(`Research done: ${allFindings.length}/${scope.angles.length} angles`)
await flowState('update', { phase: 'research' })
auditEvents.push({ phase: 'research', event: 'phase_complete', findings: allFindings.length })
} // end research skip guard

// ── Phase 3: Design (conditional UI companion) ────────────────────────
// Resume: if design already completed, skip entirely.

if (shouldSkipPhase('design')) {
  log('Phase: Design — SKIPPED (resume)')
  auditEvents.push({ phase: 'design', event: 'phase_skipped', reason: 'resume' })
} else {
phase('Design')
await flowState('event', { type: 'phase_start', phase: 'design' })
const designResearchText = allFindings.map(r => `## ${r.angle}\n\n${r.findings}`).join('\n\n---\n\n')
let classification = normalizeDesignClassification(await agent(
  `Classify whether this task needs the optional full-auto design stage.\n\n## Task\n${task}\n\n## Research\n${designResearchText}\n\n## Criteria\n${DESIGN_CLASSIFICATION_CRITERIA}\n\nReturn design_applicable=true only for explicit UI/UX/frontend visual changes. Otherwise return false and a skip_reason starting exactly with "Non-UI task:". Do not infer design work just because it could improve polish.`,
  agentOpts('design-classifier', 'Design', DESIGN_CLASSIFICATION_SCHEMA),
))

if (!classification) {
  classification = defaultDesignContext('skipped', 'Non-UI task: design classifier returned invalid or contradictory output. Design stage skipped to avoid retrofitting UI/UX work.')
  auditEvents.push({ phase: 'design', event: 'design_classifier_invalid' })
}

if (!classification.design_applicable) {
  designContext = { ...defaultDesignContext('skipped', classification.skip_reason), ...classification, status: 'skipped', paths: designPaths }
  await flowState('update', { phase: 'design', design: designContext,
    resume_cursor: { phase: 'design', design: designContext } })
  auditEvents.push({ phase: 'design', event: 'phase_complete', design_applicable: false, skip_reason: designContext.skip_reason })
} else {
  const designArtifact = await agent(
    `Create full-auto UI/UX design artifacts for this task.\n\n## Task\n${task}\n\n## Research\n${designResearchText}\n\n## Write targets\n- UI research: ${designWriteTargets.ui_research}\n- Design spec: ${designWriteTargets.design}\n- Review placeholder: ${designWriteTargets.design_review}\n\n## Canonical relative paths to report\n${JSON.stringify(designPaths, null, 2)}\n\nWrite ui-research.md and design-review.md under the controller-provided design directory, and write DESIGN.md at the project root. Do not create additional design artifacts outside these controller-provided paths. Do not install dependencies or propose a broad style-system rewrite. ui-research.md must include codebase constraints and source/decision traceability. DESIGN.md must cover visual hierarchy, responsive behavior, accessibility, interactions, keyboard/focus, and loading/empty/error/disabled/hover/active/focus states where applicable. design-review.md may start as a brief pending review note.`,
    agentOpts('write-design', 'Design', DESIGN_ARTIFACT_SCHEMA),
  )
  let designReview = await agent(
    `Review the design artifacts for implementability and scope.\n\nRead:\n- ${designWriteTargets.ui_research}\n- ${designWriteTargets.design}\n\nWrite latest review notes to ${designWriteTargets.design_review}.\n\nCheck: DESIGN.md is at the project root, research/review artifacts stay under the controller-provided design directory, no dependencies/package installs, no broad redesign/style-system overhaul, no domain-specific examples, source-backed traceability, codebase feasibility, UI states/interactions/responsive/accessibility coverage. Return REVIEW_SCHEMA.`,
    agentOpts('review-design', 'Design', REVIEW_SCHEMA),
  )
  let designIterations = 0
  while (designReview && !designReview.passed && designIterations < RETRIES && designIterations < REVIEW_RETRY_CAP) {
    await agent(
      `Revise only ${designWriteTargets.design} to fix these design-review issues. Preserve accepted decisions. Do not edit code, specs, plans, files other than DESIGN.md, or files outside the design directory.\n${JSON.stringify(designReview.issues, null, 2)}\n\nReturn a concise text summary after writing the file.`,
      { label: `fix-design-r${designIterations + 1}`, phase: 'Design', ...(model_tasks ? { model: model_tasks } : {}) },
    )
    designReview = await agent(
      `Re-review the design. Read ${designWriteTargets.ui_research}, ${designWriteTargets.design}, and ${designWriteTargets.design_review}. Verify prior issues are fixed; do not trust the revision summary.\n${JSON.stringify(designReview.issues, null, 2)}`,
      agentOpts(`review-design-r${designIterations + 1}`, 'Design', REVIEW_SCHEMA),
    )
    designIterations++
  }
  if (!designReview || !designReview.passed) {
    await flowState('update', { status: 'STOPPED_ASK_USER', phase: 'design',
      resume_cursor: { phase: 'design', design_status: 'needs_user', iteration: designIterations, paths: designPaths } })
    auditEvents.push({ phase: 'design', event: 'stopped_ask_user', design_applicable: true, iterations: designIterations })
    return {
      status: 'STOPPED_ASK_USER',
      spec: { path: null, review_passed: false },
      plan: { path: null, review_passed: false, task_count: 0 },
      execute: { completed: [], blocked: [] },
      gates: [],
      all_passed: false,
      state_file: state_file || null,
      audit_events: auditEvents,
      evidence_dir: evidence_dir || null,
      resume_cursor: { phase: 'design', design_status: 'needs_user', iteration: designIterations, paths: designPaths },
    }
  }
  designContext = {
    status: 'accepted',
    design_applicable: true,
    classification: 'ui_ux_frontend_visual',
    confidence: classification.confidence,
    evidence: classification.evidence,
    skip_reason: '',
    paths: designPaths,
    summary: (designArtifact && designArtifact.summary) || designReview.summary,
    review_passed: true,
    iteration: designIterations,
  }
  await flowState('update', { phase: 'design', design: designContext,
    resume_cursor: { phase: 'design', design: designContext } })
  auditEvents.push({ phase: 'design', event: 'phase_complete', design_applicable: true, paths: designPaths })
}
} // end design skip guard

// ── Phase 4: Synthesize Spec ─────────────────────────────────────────
// Resume: if synthesize_spec already completed, skip entirely.

if (shouldSkipPhase('synthesize_spec')) {
  log('Phase: Synthesize Spec — SKIPPED (resume)')
  auditEvents.push({ phase: 'synthesize_spec', event: 'phase_skipped', reason: 'resume' })
} else {
phase('Synthesize Spec')
await flowState('event', { type: 'phase_start', phase: 'synthesize_spec' })
const researchText = allFindings.map(r =>
  `## ${r.angle}\n\n${r.findings}\n\nKey insights:\n${r.key_insights.map(i => `- ${i}`).join('\n')}`
).join('\n\n---\n\n')

const openQuestionsText = allFindings
  .flatMap(r => r.open_questions).filter(Boolean)
  .map(q => `- ${q}`).join('\n')

spec = await agent(
  `Write a complete, implementable development spec based on this research.

## Task

${task}

## Research

${researchText}

## Open Questions — resolve with best-guess defaults

${openQuestionsText || 'None'}

## Design Context

${designContext && designContext.design_applicable ? `Accepted DESIGN.md: ${designContext.paths.design}\nUI research: ${designContext.paths.ui_research}\nDesign review: ${designContext.paths.design_review}\nSummary: ${designContext.summary || 'Accepted design artifacts available'}\nUse these artifacts for UI/UX requirements and implementation constraints.` : `Design stage skipped. ${designContext && designContext.skip_reason ? designContext.skip_reason : 'Do not invent UI/UX requirements unless the task itself requires them.'}`}

## Instructions

1. Resolve open questions with reasonable defaults. Record your decisions.
2. Decision principles: YAGNI scope, existing codebase patterns first,
   simplest architecture, match project conventions
3. Check whether this task requires art/image assets. If yes, include an Asset Requirements section that references skills/auto-mode/references/image-generation.md and records concrete asset briefs, count, size/aspect, quality, output path, and evidence requirements. If no assets are needed, state "Asset Requirements: none".
4. Write spec to: ${specPath}
5. Structure:

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

## Asset Requirements
(none, or visual assets needed with brief/count/size/quality/output path/evidence; use skills/auto-mode/references/image-generation.md)

## Acceptance Criteria
(numbered, verifiable — "when user does X, system does Y")
\`\`\`

Use the Write tool to save the file. Return the path and summary.`,
  agentOpts('synthesize-spec', 'Synthesize Spec', SPEC_SCHEMA),
)

log(`Spec: ${spec.spec_path}`)
await flowState('update', { phase: 'synthesize_spec', spec_path: spec.spec_path })
auditEvents.push({ phase: 'synthesize_spec', event: 'phase_complete', spec_path: spec.spec_path })
} // end synthesize_spec skip guard

// ── Phase 4: Review Spec ─────────────────────────────────────────────
// Resume: if review_spec already completed, skip entirely.

if (shouldSkipPhase('review_spec')) {
  log('Phase: Review Spec — SKIPPED (resume)')
  auditEvents.push({ phase: 'review_spec', event: 'phase_skipped', reason: 'resume' })
} else {
phase('Review Spec')
await flowState('event', { type: 'phase_start', phase: 'review_spec' })
specReview = await agent(
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
while (!specReview.passed && specIterations < RETRIES && specIterations < REVIEW_RETRY_CAP) {
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

// STOPPED_ASK_USER: review cap exhausted, cannot resolve spec issues
if (!specReview.passed && specIterations >= REVIEW_RETRY_CAP) {
  await flowState('update', { status: 'STOPPED_ASK_USER', phase: 'review_spec',
    resume_cursor: { phase: 'review_spec', iteration: specIterations, spec_path: spec.spec_path } })
  auditEvents.push({ phase: 'review_spec', event: 'stopped_ask_user', iterations: specIterations })
  return {
    status: 'STOPPED_ASK_USER',
    spec: { path: spec.spec_path, review_passed: false },
    plan: { path: null, review_passed: false, task_count: 0 },
    execute: { completed: [], blocked: [] },
    gates: [],
    all_passed: false,
    state_file: state_file || null,
    audit_events: auditEvents,
    evidence_dir: evidence_dir || null,
    resume_cursor: { phase: 'review_spec', iteration: specIterations, spec_path: spec.spec_path },
  }
}
await flowState('update', { phase: 'review_spec' })
auditEvents.push({ phase: 'review_spec', event: 'phase_complete', passed: specReview.passed })
} // end review_spec skip guard

// ── Phase 5: Write Plan ──────────────────────────────────────────────
// Resume: if write_plan already completed, skip entirely.

if (shouldSkipPhase('write_plan')) {
  log('Phase: Write Plan — SKIPPED (resume)')
  auditEvents.push({ phase: 'write_plan', event: 'phase_skipped', reason: 'resume' })
} else {
phase('Write Plan')
await flowState('event', { type: 'phase_start', phase: 'write_plan' })
planResult = await agent(
  `Decompose the spec into an implementation plan. Write to ${planPath}.

1. Read the spec at ${spec.spec_path}
2. If accepted design context exists, read ${designContext && designContext.design_applicable ? designContext.paths.design : 'no DESIGN.md — design skipped'} and preserve those UI constraints; if design was skipped, do not create design tasks.
3. Break into atomic tasks. Each task: distinct files, clear description,
   implementation details, depends_on list, verification command
3. Rules: auto-split independent subsystems; each task completable in one session;
   every spec requirement covered by at least one task
4. If the spec requires art/image assets, create explicit artist task(s). Artist tasks must reference skills/auto-mode/prompts/artist-prompt.md and skills/auto-mode/references/image-generation.md, use scripts/generate-image.py, list output paths as files, set runtime_evidence_required to required, and verify generated files plus manifest evidence. If no assets are needed, do not create artist tasks.
5. Format each task as:

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
await flowState('update', { phase: 'write_plan', plan_path: planResult.plan_path,
  progress: { tasks_total: planResult.task_count } })
auditEvents.push({ phase: 'write_plan', event: 'phase_complete',
  plan_path: planResult.plan_path, task_count: planResult.task_count })
} // end write_plan skip guard

// ── Phase 6: Review Plan ─────────────────────────────────────────────
// Resume: if review_plan already completed, skip entirely.

if (shouldSkipPhase('review_plan')) {
  log('Phase: Review Plan — SKIPPED (resume)')
  auditEvents.push({ phase: 'review_plan', event: 'phase_skipped', reason: 'resume' })
} else {
phase('Review Plan')
await flowState('event', { type: 'phase_start', phase: 'review_plan' })
planReview = await agent(
  `Review the plan at ${planResult.plan_path} against the spec at ${specPath}.

Verify: every spec requirement covered, dependencies correct (no cycles,
no missing), each task atomic and independently completable.

Critical: missing requirement, broken dependency.
Important: task too large, unclear scope.
Minor: wording.`,
  agentOpts('review-plan', 'Review Plan', REVIEW_SCHEMA),
)

let planIterations = 0
while (!planReview.passed && planIterations < RETRIES && planIterations < REVIEW_RETRY_CAP) {
  log(`Plan issues: ${planReview.issues.length} — revising`)
  await agent(
    `Fix the plan at ${planResult.plan_path}:
${JSON.stringify(planReview.issues, null, 2)}
Read plan and spec. Edit only what the issues describe. Return a concise text summary after writing the file.`,
    { label: `fix-plan-r${planIterations + 1}`, phase: 'Review Plan', ...(model_tasks ? { model: model_tasks } : {}) },
  )
  planReview = await agent(
    `Re-review the plan. Verify these issues are fixed:
${JSON.stringify(planReview.issues, null, 2)}
Read the plan file independently.`,
    agentOpts(`review-plan-r${planIterations + 1}`, 'Review Plan', REVIEW_SCHEMA),
  )
  planIterations++
}
log(`Plan review: ${planReview.passed ? 'PASSED' : `STALLED (${planIterations} itrs)`}`)

// STOPPED_ASK_USER: plan review cap exhausted
if (!planReview.passed && planIterations >= REVIEW_RETRY_CAP) {
  await flowState('update', { status: 'STOPPED_ASK_USER', phase: 'review_plan',
    resume_cursor: { phase: 'review_plan', iteration: planIterations, plan_path: planResult.plan_path } })
  auditEvents.push({ phase: 'review_plan', event: 'stopped_ask_user', iterations: planIterations })
  return {
    status: 'STOPPED_ASK_USER',
    spec: { path: spec.spec_path, review_passed: specReview.passed },
    plan: { path: planResult.plan_path, review_passed: false, task_count: planResult.task_count },
    execute: { completed: [], blocked: [] },
    gates: [],
    all_passed: false,
    state_file: state_file || null,
    audit_events: auditEvents,
    evidence_dir: evidence_dir || null,
    resume_cursor: { phase: 'review_plan', iteration: planIterations, plan_path: planResult.plan_path },
  }
}
await flowState('update', { phase: 'review_plan' })
auditEvents.push({ phase: 'review_plan', event: 'phase_complete', passed: planReview.passed })
} // end review_plan skip guard

// ── Phase 7: Parse Plan — extract structured tasks ────────────────────
// Resume: if parse_plan already completed, skip entirely.

if (shouldSkipPhase('parse_plan')) {
  log('Phase: Parse Plan — SKIPPED (resume)')
  auditEvents.push({ phase: 'parse_plan', event: 'phase_skipped', reason: 'resume' })
} else {
phase('Parse Plan')
await flowState('event', { type: 'phase_start', phase: 'parse_plan' })
parsed = await agent(
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
await flowState('update', { phase: 'parse_plan', groups: parsed.groups,
  task_states: Object.fromEntries(Object.keys(parsed.tasks).map(k => [k, {
    task_id: k,
    status: 'queued',
    attempts: 0,
    files_modified: [],
    evidence_paths: [],
    commit_sha: '',
  }])) })
auditEvents.push({ phase: 'parse_plan', event: 'phase_complete',
  groups: parsed.groups.length, tasks: Object.keys(parsed.tasks).length })
} // end parse_plan skip guard

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
    gates: CANONICAL_GATES.map(name => makeGateRecord(name, false, 'Skipped — plan validation failed')),
    all_passed: false,
    validation_errors: planValidation.errors,
  }
}
log('Plan validation passed')

// ── Phase 8: Execute ───────────────────────────────────────────
// Inlined execute-plan: implement → spec review → code review → final review

if (shouldSkipPhase('execute')) {
  log('Phase: Execute — SKIPPED (resume)')
  auditEvents.push({ phase: 'execute', event: 'phase_skipped', reason: 'resume' })
} else {
phase('Execute')
await flowState('event', { type: 'phase_start', phase: 'execute' })
log('Starting execute phase...')

// Execute-phase local variables
const MAX_RETRIES = RETRIES
const resumeState = normalizeResumeState(resume_from || {})
const result_replay = resumeTaskReplay || []

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

      // Resume: skip already-passed tasks (result_replay from state)
      if (result_replay.includes(taskId)) {
        log(taskId + ': REPLAYED — already passed in prior run, skipping')
        return {
          ...task,
          id: taskId,
          impl: { status: 'DONE', summary: 'Replayed from prior run', files_modified: task.files || [], commit_sha: '', test_results: '', concerns: [], evidence_paths: [], verification_commands: task.verification || [] },
          spec_review: { passed: true, issues: [], summary: 'Replayed' },
          code_review: { passed: true, issues: [], summary: 'Replayed' },
          spec_passed: true,
          code_passed: true,
          _iterations_spec: 0,
          _iterations_code: 0,
          _replayed: true,
        }
      }

      return pipeline(
        [task],

        // Stage 1: Implement (with schema retry)
        async (t) => {
          const attemptLabel = 'implement:' + t.id
          captureAttemptBase(args, t, t, attemptLabel)
          let result = await agentWithSchemaRetry(
            implementPrompt(t),
            agentOpts(attemptLabel, 'Implement', IMPLEMENT_RESULT),
            ESCALATION_ATTEMPTS.schema_retry,
          )
          recordAttemptDiffEvidence(args, t, t, attemptLabel)

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

        // Stage 2: Evidence Gate + Spec Review (with review threshold enforcement)
        async (ctx) => {
          const { impl, id } = ctx
          if (!impl || impl.status === 'BLOCKED') {
            return { ...ctx, spec_review: null, spec_passed: false, _blocked: true, _reason: (impl && impl.blocker_detail) || 'BLOCKED' }
          }

          let controllerEvidence = controllerEvidenceFromAttempts(ctx)
          let implementationEvidence = validateImplementationEvidence(ctx, impl, controllerEvidence, null)
          if (!implementationEvidence.passed) {
            return { ...ctx, implementation_evidence: controllerEvidence, evidence_validation: implementationEvidence, spec_review: null, spec_passed: false, _blocked: true, _reason: implementationEvidence.reasons.join('; '), _evidence_blocked: true }
          }
          if (!implementationEvidenceCleanPass(implementationEvidence)) {
            impl.concerns = [...(impl.concerns || []), ...implementationEvidence.limitations]
            impl.evidence_validation = implementationEvidence
            impl.limitations = implementationEvidence.limitations
          }

          let review = await agentWithSchemaRetry(
            specReviewPrompt(ctx, impl),
            agentOpts('spec-review:' + id, 'Spec Review', REVIEW_RESULT),
            0,
          )
          review = normalizeReviewResult(review, 'spec_review', id, null)

          let iterations = 0
          ctx.spec_fix_attempts = 0
          const hasBlocking = () => hasBlockingIssues(review, 'spec_review', risk)

          while (review && hasBlocking() && ctx.spec_fix_attempts < MAX_RETRIES) {
            const blockingIssues = review.issues.filter(i =>
              isIssueBlocking('spec_review', risk, i.severity, i.blocking)
            )
            log(id + ': spec review found ' + blockingIssues.length + ' blocking issue(s) — fixing')
            const fixAttempt = ctx.spec_fix_attempts + 1
            const fixLabel = 'fix-spec:' + id + '-r' + fixAttempt
            captureAttemptBase(args, ctx, ctx, fixLabel)
            const updated = await agentWithSchemaRetry(
              fixPrompt(blockingIssues, fixIssueFiles(blockingIssues), ctx, impl, 'spec_fix', fixAttempt),
              agentOpts(fixLabel, 'Spec Review', FIX_RESULT),
              0,
            )
            recordAttemptDiffEvidence(args, ctx, ctx, fixLabel)
            const fixContract = validateFixResultContract(updated, blockingIssues)
            if (!fixContract.passed) {
              return { ...ctx, implementation_evidence: controllerEvidenceFromAttempts(ctx), evidence_validation: fixContract, spec_review: null, spec_passed: false, _blocked: true, _reason: fixContract.reasons.join('; '), _fix_result_blocked: true }
            }
            ctx.impl = { ...ctx.impl, ...updated }
            controllerEvidence = controllerEvidenceFromAttempts(ctx)
            implementationEvidence = validateImplementationEvidence(ctx, ctx.impl, controllerEvidence, null)
            if (!implementationEvidence.passed) {
              return { ...ctx, implementation_evidence: controllerEvidence, evidence_validation: implementationEvidence, spec_review: null, spec_passed: false, _blocked: true, _reason: implementationEvidence.reasons.join('; '), _evidence_blocked: true }
            }
            if (!implementationEvidenceCleanPass(implementationEvidence)) {
              ctx.impl.concerns = [...(ctx.impl.concerns || []), ...implementationEvidence.limitations]
              ctx.impl.evidence_validation = implementationEvidence
              ctx.impl.limitations = implementationEvidence.limitations
            }

            const priorSpecReview = review
            review = await agentWithSchemaRetry(
              specReviewPrompt(ctx, ctx.impl, priorSpecReview),
              agentOpts('spec-review:' + id + '-r' + fixAttempt, 'Spec Review', REVIEW_REREVIEW_RESULT),
              0,
            )
            review = normalizeReviewResult(review, 'spec_review', id, priorSpecReview)
            if (review) review._prior_blocking_issue_ids = blockingIssues.map(issue => issue && issue.id).filter(Boolean)
            ctx.spec_fix_attempts = fixAttempt
            iterations = ctx.spec_fix_attempts
          }

          const specPassed = review ? !hasBlocking() && !hasBlockingRereviewMetadata(review) : false
          const exhausted = ctx.spec_fix_attempts >= MAX_RETRIES && !specPassed

          return {
            ...ctx,
            implementation_evidence: controllerEvidence,
            evidence_validation: implementationEvidence,
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
            codeReviewPrompt(ctx.impl, ctx.id, ctx),
            agentOpts('code-review:' + ctx.id, 'Code Review', REVIEW_RESULT),
            0,
          )
          review = normalizeReviewResult(review, 'code_review', ctx.id, ctx.spec_review)

          let iterations = 0
          ctx.code_fix_attempts = 0
          const hasBlocking = () => hasBlockingIssues(review, 'code_review', risk)

          while (review && hasBlocking() && ctx.code_fix_attempts < MAX_RETRIES) {
            const blockingIssues = review.issues.filter(i =>
              isIssueBlocking('code_review', risk, i.severity, i.blocking)
            )
            log(ctx.id + ': code review found ' + blockingIssues.length + ' blocking issue(s) — fixing')
            const fixAttempt = ctx.code_fix_attempts + 1
            const fixLabel = 'fix-code:' + ctx.id + '-r' + fixAttempt
            captureAttemptBase(args, ctx, ctx, fixLabel)
            const updated = await agentWithSchemaRetry(
              fixPrompt(blockingIssues, fixIssueFiles(blockingIssues), ctx, ctx.impl, 'code_fix', fixAttempt),
              agentOpts(fixLabel, 'Code Review', FIX_RESULT),
              0,
            )
            recordAttemptDiffEvidence(args, ctx, ctx, fixLabel)
            const fixContract = validateFixResultContract(updated, blockingIssues)
            if (!fixContract.passed) {
              return { ...ctx, implementation_evidence: controllerEvidenceFromAttempts(ctx), evidence_validation: fixContract, code_review: null, code_passed: false, _blocked: true, _reason: fixContract.reasons.join('; '), _fix_result_blocked: true }
            }
            ctx.impl = { ...ctx.impl, ...updated }

            const controllerEvidence = controllerEvidenceFromAttempts(ctx)
            const implementationEvidence = validateImplementationEvidence(ctx, ctx.impl, controllerEvidence, ctx.spec_review)
            if (!implementationEvidence.passed) {
              return { ...ctx, implementation_evidence: controllerEvidence, evidence_validation: implementationEvidence, code_review: null, code_passed: false, _blocked: true, _reason: implementationEvidence.reasons.join('; '), _evidence_blocked: true }
            }
            if (!implementationEvidenceCleanPass(implementationEvidence)) {
              ctx.impl.concerns = [...(ctx.impl.concerns || []), ...implementationEvidence.limitations]
              ctx.impl.evidence_validation = implementationEvidence
              ctx.impl.limitations = implementationEvidence.limitations
            }
            ctx.implementation_evidence = controllerEvidence
            ctx.evidence_validation = implementationEvidence

            const priorCodeReview = review
            review = await agentWithSchemaRetry(
              codeReviewPrompt(ctx.impl, ctx.id, ctx, priorCodeReview),
              agentOpts('code-review:' + ctx.id + '-r' + fixAttempt, 'Code Review', REVIEW_REREVIEW_RESULT),
              0,
            )
            review = normalizeReviewResult(review, 'code_review', ctx.id, priorCodeReview)
            if (review) review._prior_blocking_issue_ids = blockingIssues.map(issue => issue && issue.id).filter(Boolean)
            ctx.code_fix_attempts = fixAttempt
            iterations = ctx.code_fix_attempts
          }

          const codePassed = review ? !hasBlocking() && !hasBlockingRereviewMetadata(review) : false
          const exhausted = ctx.code_fix_attempts >= MAX_RETRIES && !codePassed

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
let finalFixAttempts = 0
let tasksStaleAfterFinalFixList = []
let finalReviewNextAction = ''
let finalBranchDiffEvidence = null
if (partitions.completed.length === totalTasks && allOtherPartitionsEmpty && totalTasks > 0) {
  phase('Final Review')
  const allFiles = partitions.completed.flatMap(r => r.files || r.evidence?.files_modified || []).filter(Boolean)
  const allIds = partitions.completed.map(r => r.id).join(', ')
  const finalTask = { id: 'final', description: 'Final review for ' + allIds, files: allFiles }
  let finalImpl = { summary: 'Entire implementation: ' + allIds, files_modified: allFiles }
  let branchDiffEvidence = collectFinalBranchDiffEvidence(args, finalTask, finalImpl)
  finalBranchDiffEvidence = branchDiffEvidence

  finalReview = await agentWithSchemaRetry(
    finalReviewPrompt(partitions.completed, finalTask, finalImpl),
    agentOpts('final-review', 'Final Review', REVIEW_RESULT),
    0,
  )
  finalReview = normalizeFinalReview(finalReview, branchDiffEvidence)

  while (finalReview && finalReview.passed === false && finalFixAttempts < MAX_RETRIES) {
    const blockingIssues = (finalReview.issues || []).filter(i =>
      isIssueBlocking('final_review', 'medium', i.severity, i.blocking)
    )
    if (blockingIssues.length === 0) break
    const fixAttempt = finalFixAttempts + 1
    const fixLabel = 'fix-final-r' + fixAttempt
    captureAttemptBase(args, finalTask, finalTask, fixLabel)
    const updated = await agentWithSchemaRetry(
      fixPrompt(blockingIssues, fixIssueFiles(blockingIssues), finalTask, finalImpl, 'final_fix', fixAttempt),
      agentOpts(fixLabel, 'Final Review', FIX_RESULT),
      0,
    )
    recordAttemptDiffEvidence(args, finalTask, finalTask, fixLabel)
    const fixContract = validateFixResultContract(updated, blockingIssues)
    finalFixAttempts = fixAttempt
    if (!fixContract.passed) {
      finalReview = normalizeFinalReview({
        passed: false,
        issues: blockingIssues,
        summary: fixContract.reasons.join('; '),
        unresolved_issue_ids: blockingIssues.map(issue => issue.id).filter(Boolean),
      }, branchDiffEvidence)
      break
    }
    finalImpl = { ...finalImpl, ...updated, attempt_diff_evidence: finalTask.attempt_diff_evidence || [] }
    const touchedFiles = collectFinalFixTouchedFiles(finalTask)
    const staleAfterAttempt = tasksStaleAfterFinalFix(partitions.completed, touchedFiles)
    tasksStaleAfterFinalFixList = mergeTasksStaleAfterFinalFix(tasksStaleAfterFinalFixList, staleAfterAttempt)
    const invalidatesEvidence = finalFixInvalidatesTaskEvidence(partitions.completed, tasksStaleAfterFinalFixList)
    if (invalidatesEvidence) finalReviewNextAction = 'rerun_task_review'
    const priorFinalReview = finalReview
    branchDiffEvidence = collectFinalBranchDiffEvidence(args, finalTask, finalImpl)
    finalBranchDiffEvidence = branchDiffEvidence
    finalReview = await agentWithSchemaRetry(
      finalReviewPrompt(partitions.completed, finalTask, finalImpl, priorFinalReview),
      agentOpts('final-review-r' + fixAttempt, 'Final Review', REVIEW_REREVIEW_RESULT),
      0,
    )
    finalReview = normalizeFinalReview(finalReview, branchDiffEvidence)
    if (finalReview) finalReview._prior_blocking_issue_ids = blockingIssues.map(issue => issue && issue.id).filter(Boolean)
    if (hasBlockingRereviewMetadata(finalReview)) finalReview.passed = false
    if (invalidatesEvidence) {
      finalReview.passed = false
      finalReview.next_action = 'rerun_task_review'
      finalReview.scope_concerns = [...(finalReview.scope_concerns || []), 'final_fix_invalidates_unverified_task_evidence']
    }
  }

  if (finalReview) {
    finalReview.final_fix_attempts = finalFixAttempts
    finalReview.tasks_stale_after_final_fix = tasksStaleAfterFinalFixList
    if (finalReviewNextAction && !finalReview.next_action) finalReview.next_action = finalReviewNextAction
    if (finalReview.passed === false) finalReview.unresolved_issue_ids = unresolvedIssueIds(finalReview)
  }
}

// ── Build state_patch for resume support ──────────────────────────────

const resultEntries = [
  ...partitions.passed,
  ...partitions.blocked,
  ...partitions.stalled,
  ...partitions.failed_review,
  ...partitions.needs_escalation,
]

const attemptDiffEvidence = resultEntries.flatMap(e => e.attempt_diff_evidence || e.impl?.attempt_diff_evidence || [])
const taskEvidenceValidations = resultEntries.filter(e => e.evidence_validation).map(e => ({
  id: e.id,
  status: e.evidence_validation.status,
  reasons: e.evidence_validation.reasons || [],
  limitations: e.evidence_validation.limitations || [],
  evidence: e.evidence_validation.evidence || {},
}))
const attemptBaseEvidence = resultEntries.filter(e => e.task_attempt_base_sha || e.task_attempt_base_capture_failed).map(e => ({
  id: e.id,
  task_attempt_base_sha: e.task_attempt_base_sha,
  task_attempt_base_dirty: !!e.task_attempt_base_dirty,
  task_attempt_base_capture_failed: e.task_attempt_base_capture_failed || '',
}))
const canonicalFinalReview = finalReview || resumeState.final_review
const finalReviewRun = finalReview !== null || resumeState.final_review_run === true
const finalReviewBlocked = canonicalFinalReview ? !!(canonicalFinalReview.passed === false || resumeState.final_review_blocked) : false
const finalReviewEvidence = finalReview && finalReview.branch_diff_evidence ? [finalReview.branch_diff_evidence] : (finalBranchDiffEvidence ? [finalBranchDiffEvidence] : resumeState.final_review_evidence)
const finalReviewFromResume = finalReview === null && finalBranchDiffEvidence === null
const finalReviewBlockingIssues = finalReviewBlocked ? ((canonicalFinalReview && canonicalFinalReview.issues || []).filter(issue => isIssueBlocking('final_review', 'medium', issue.severity, issue.blocking)).concat(finalReviewFromResume ? (resumeState.final_review_blocking_issues || []) : [])) : []
const unresolvedFinalReviewIssues = finalReviewBlocked ? [...new Set([...(canonicalFinalReview ? unresolvedIssueIds(canonicalFinalReview) : []), ...(finalReviewFromResume ? (resumeState.unresolved_final_review_issues || []) : [])])] : []
const finalDiffEvidence = finalReviewEvidence[0] || {}
const iterations = {
  final_fix_attempts: finalFixAttempts,
  task_fix_attempts: resultEntries.map(e => ({ id: e.id, spec_fix_attempts: e.spec_fix_attempts || 0, code_fix_attempts: e.code_fix_attempts || 0 })),
}

const state_patch = {
  task_attempt_bases: attemptBaseEvidence,
  task_attempt_diff_evidence: attemptDiffEvidence,
  task_evidence_validations: taskEvidenceValidations,
  partitions: {
    passed: partitions.passed.map(e => e.id),
    completed: partitions.completed.map(e => e.id),
    blocked: partitions.blocked.map(e => e.id),
    stalled: partitions.stalled.map(e => e.id),
    failed_review: partitions.failed_review.map(e => e.id),
    needs_escalation: partitions.needs_escalation.map(e => e.id),
  },
  total_tasks: totalTasks,
  final_review_run: finalReviewRun,
  final_review: canonicalFinalReview,
  final_review_evidence: finalReviewEvidence,
  final_review_blocking_issues: finalReviewBlockingIssues,
  unresolved_final_review_issues: unresolvedFinalReviewIssues,
  final_review_blocked: finalReviewBlocked,
  base_ref: finalDiffEvidence.base_ref || args.base_ref || resumeState.base_ref || '',
  base_sha: finalDiffEvidence.base_sha || args.base_sha || resumeState.base_sha || '',
  head_sha: finalDiffEvidence.head_sha || resumeState.head_sha || '',
  dirty: finalDiffEvidence.dirty !== undefined ? !!finalDiffEvidence.dirty : resumeState.dirty === true,
  diff_command: finalDiffEvidence.diff_command || resumeState.diff_command || '',
  diff_files: finalDiffEvidence.diff_files || resumeState.diff_files || [],
  diff_verified: finalDiffEvidence.diff_verified === true || resumeState.diff_verified === true,
  diff_truncated: finalDiffEvidence.diff_truncated === true || resumeState.diff_truncated === true,
  evidence_dir: args.evidence_dir || resumeState.evidence_dir || '',
  iterations,
  tasks_stale_after_final_fix: tasksStaleAfterFinalFixList,
  final_review_unresolved_issue_ids: unresolvedFinalReviewIssues,
  final_fix_attempts: finalFixAttempts,
  enforcement_mode: ENFORCEMENT_MODE,
  resume_warnings: resumeState.warnings || [],
}

return {
  passed: partitions.passed,
  completed: partitions.completed,
  blocked: partitions.blocked,
  stalled: partitions.stalled,
  failed_review: partitions.failed_review,
  needs_escalation: partitions.needs_escalation,
  final_review_run: finalReviewRun,
  final_review: canonicalFinalReview,
  state_patch,
}



log(`Execute: ${executeResult.completed.length} completed, ${executeResult.blocked.length} blocked`)
await flowState('update', { phase: 'execute',
  progress: { tasks_passed: executeResult.completed.length,
    tasks_total: executeResult.completed.length + executeResult.blocked.length } })
auditEvents.push({ phase: 'execute', event: 'phase_complete',
  completed: executeResult.completed.length, blocked: executeResult.blocked.length })
} // end execute skip guard

// ── Phase 9: Gates ───────────────────────────────────────────────────

phase('Gates')
await flowState('event', { type: 'phase_start', phase: 'gates' })

// Gate states: map from canonical name -> gate record
const gateStates = {}
let gateCursor = 0

// Resume support: skip already-passed gates unless invalidated
const resumeGateCursor = (resume_from && resume_from.cursor && resume_from.cursor.gate_cursor) || 0
const resumeGateStates = (resume_from && resume_from.cursor && resume_from.cursor.gate_states) || {}

function isGateAlreadyPassed(gateName, index) {
  return index < resumeGateCursor && resumeGateStates[gateName] && resumeGateStates[gateName].passed
}

function priorGatePassed() {
  return gateCursor === 0 || (gateStates[GATE_NAMES[gateCursor - 1]] && gateStates[GATE_NAMES[gateCursor - 1]].passed)
}

async function recordGate(gateName, passed, detail, extra) {
  const record = makeGateRecord(gateName, passed, detail, extra)
  gateStates[gateName] = record
  gateCursor = GATE_NAMES.indexOf(gateName) + 1
  const gatesArray = GATE_NAMES.map(n => gateStates[n] || makeGateRecord(n, false, 'Pending'))
  const passedCount = gatesArray.filter(g => g.passed).length
  await flowState('update', {
    gate_states: gatesArray,
    progress: { gates_passed: passedCount, gates_total: 7 },
    resume_cursor: { phase: 'gates', gate_cursor: gateCursor, gate_states: gateStates },
  })
  return record
}

// ── Gate 1: tasks_executed ──────────────────────────────────────────
if (isGateAlreadyPassed(GATE_TASKS_EXECUTED, 0)) {
  gateStates[GATE_TASKS_EXECUTED] = resumeGateStates[GATE_TASKS_EXECUTED]
  gateCursor = 1
  log('Gate 1 (tasks_executed): SKIPPED — already passed')
} else {
  const g1Passed = executeResult.blocked.length === 0
  const g1Detail = `${executeResult.completed.length} completed, ${executeResult.blocked.length} blocked`
  const g1Extra = {
    iterations: 1,
    last_failure: g1Passed ? null : g1Detail,
    next_action: g1Passed ? 'proceed' : 'retry_tasks',
  }
  await recordGate(GATE_TASKS_EXECUTED, g1Passed, g1Detail, g1Extra)
  log(`Gate 1 (tasks_executed): ${g1Passed ? 'PASSED' : 'FAILED'}`)
}

// ── Gate 2: reviews_passed ──────────────────────────────────────────
if (isGateAlreadyPassed(GATE_REVIEWS_PASSED, 1)) {
  gateStates[GATE_REVIEWS_PASSED] = resumeGateStates[GATE_REVIEWS_PASSED]
  gateCursor = 2
  log('Gate 2 (reviews_passed): SKIPPED — already passed')
} else if (priorGatePassed()) {
  const g2Passed = executeResult.completed.length > 0 &&
    executeResult.completed.every(r => r.code_passed)
  const g2Detail = g2Passed ? 'All reviews passed' : 'Some reviews have unresolved issues'
  const g2Extra = {
    iterations: 1,
    last_failure: g2Passed ? null : g2Detail,
    next_action: g2Passed ? 'proceed' : 'fix_reviews',
  }
  await recordGate(GATE_REVIEWS_PASSED, g2Passed, g2Detail, g2Extra)
  log(`Gate 2 (reviews_passed): ${g2Passed ? 'PASSED' : 'FAILED'}`)
} else {
  await recordGate(GATE_REVIEWS_PASSED, false, 'Skipped — tasks_executed not passed', { iterations: 0, next_action: 'unblock_gate_1' })
  log('Gate 2 (reviews_passed): SKIPPED — gate 1 not passed')
}

// ── Gate 3: tests_pass ──────────────────────────────────────────────
if (isGateAlreadyPassed(GATE_TESTS_PASS, 2)) {
  gateStates[GATE_TESTS_PASS] = resumeGateStates[GATE_TESTS_PASS]
  gateCursor = 3
  log('Gate 3 (tests_pass): SKIPPED — already passed')
} else if (priorGatePassed()) {
  let passed = false
  let detail = ''
  let lastFailure = null
  let lastFix = null
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
    if (!passed) {
      lastFailure = detail
      lastFix = r.fix_applied || ''
    }
    iters++
  }

  await recordGate(GATE_TESTS_PASS, passed, detail, {
    iterations: iters,
    last_failure: lastFailure,
    last_fix: lastFix,
    next_action: passed ? 'proceed' : 'fix_tests_or_escalate',
    fix_applied: iters > 1 ? `${iters} attempts` : '',
  })
  log(`Gate 3 (tests_pass): ${passed ? 'PASSED' : `FAILED after ${iters} attempts`}`)
} else {
  await recordGate(GATE_TESTS_PASS, false, 'Skipped — reviews_passed not passed', { iterations: 0, next_action: 'unblock_gate_2' })
  log('Gate 3 (tests_pass): SKIPPED — gate 2 not passed')
}

// ── Gate 4: runtime_evidence (writes manifest) ─────────────────────
if (isGateAlreadyPassed(GATE_RUNTIME_EVIDENCE, 3)) {
  gateStates[GATE_RUNTIME_EVIDENCE] = resumeGateStates[GATE_RUNTIME_EVIDENCE]
  gateCursor = 4
  log('Gate 4 (runtime_evidence): SKIPPED — already passed')
} else if (priorGatePassed()) {
  let passed = false
  let detail = ''
  let lastFailure = null
  let lastFix = null
  let iters = 0
  let manifest = null

  while (!passed && iters < GATE_RETRIES) {
    const r = await agent(
      `Verify the implementation works at runtime.
1. If this is a runnable project: build and run a smoke test
   (start server, run CLI, etc.), capture exit code/output/crashes
2. If library/config-only: report as unverifiable (auto-pass)
Report what you observed.`,
      agentOpts('gate-4-runtime', 'Gates', GATE_RESULT),
    )
    passed = r.passed
    detail = r.detail
    if (!passed) {
      lastFailure = detail
      lastFix = r.fix_applied || ''
    }
    iters++
  }

  // Build runtime manifest
  manifest = {
    commands: detail || 'N/A',
    exit_codes: passed ? [0] : [1],
    logs: [],
    screenshots: [],
    artifacts: [],
    crash: !passed && (detail && detail.toLowerCase().includes('crash')),
    hang: !passed && (detail && detail.toLowerCase().includes('hang')),
    unverified_acceptance_items: [],
    blocking_risks: passed ? [] : [detail],
    generated_at: new Date().toISOString(),
  }

  if (evidence_dir) {
    await flowState('manifest', { artifacts: [], summary: manifest })
  }

  await recordGate(GATE_RUNTIME_EVIDENCE, passed, detail, {
    iterations: iters,
    last_failure: lastFailure,
    last_fix: lastFix,
    evidence_paths: evidence_dir ? [evidence_dir] : [],
    next_action: passed ? 'proceed' : 'fix_runtime_or_escalate',
    fix_applied: iters > 1 ? `${iters} attempts` : '',
    manifest,
  })
  log(`Gate 4 (runtime_evidence): ${passed ? 'PASSED' : `FAILED after ${iters} attempts`}`)
} else {
  await recordGate(GATE_RUNTIME_EVIDENCE, false, 'Skipped — tests_pass not passed', { iterations: 0, next_action: 'unblock_gate_3' })
  log('Gate 4 (runtime_evidence): SKIPPED — gate 3 not passed')
}

// ── Gate 5: spec_verified ───────────────────────────────────────────
if (isGateAlreadyPassed(GATE_SPEC_VERIFIED, 4)) {
  gateStates[GATE_SPEC_VERIFIED] = resumeGateStates[GATE_SPEC_VERIFIED]
  gateCursor = 5
  log('Gate 5 (spec_verified): SKIPPED — already passed')
} else if (priorGatePassed()) {
  let passed = false
  let detail = ''
  let lastFailure = null
  let lastFix = null
  let iters = 0

  while (!passed && iters < GATE_RETRIES) {
    const r = await agent(
      `Verify the implementation against the spec at ${specPath}.
Read the spec line by line. For each requirement, find the code that satisfies it.
Report: passed (every requirement verified) or failed with specific gaps.`,
      agentOpts('gate-5-spec-verify', 'Gates', GATE_RESULT),
    )
    passed = r.passed
    detail = r.detail
    if (!passed) {
      lastFailure = detail
      lastFix = r.fix_applied || ''
    }
    iters++
  }

  await recordGate(GATE_SPEC_VERIFIED, passed, detail, {
    iterations: iters,
    last_failure: lastFailure,
    last_fix: lastFix,
    evidence_paths: [specPath],
    next_action: passed ? 'proceed' : 'fix_spec_gaps',
    fix_applied: iters > 1 ? `${iters} attempts` : '',
  })
  log(`Gate 5 (spec_verified): ${passed ? 'PASSED' : `FAILED after ${iters} attempts`}`)
} else {
  await recordGate(GATE_SPEC_VERIFIED, false, 'Skipped — runtime_evidence not passed', { iterations: 0, next_action: 'unblock_gate_4' })
  log('Gate 5 (spec_verified): SKIPPED — gate 4 not passed')
}

// ── Gate 6: final_review (requires latest cross-task review) ────────
if (isGateAlreadyPassed(GATE_FINAL_REVIEW, 5)) {
  gateStates[GATE_FINAL_REVIEW] = resumeGateStates[GATE_FINAL_REVIEW]
  gateCursor = 6
  log('Gate 6 (final_review): SKIPPED — already passed')
} else if (priorGatePassed()) {
  // Must verify cross-task Final Review ran AFTER all tasks passed
  const executeHadFinalReview = executeResult.final_review &&
    executeResult.final_review.passed === true &&
    executeResult.completed.length > 0 &&
    executeResult.completed.every(r => r.code_passed)

  let passed = false
  let detail = ''
  let lastFailure = null
  let lastFix = null
  let iters = 0

  // If execute phase already had a valid final review, use it
  if (executeHadFinalReview) {
    passed = true
    detail = 'Final review from execute phase confirmed (all tasks passed before review)'
  } else {
    // Run a fresh cross-task final review
    const review = await agent(
      `Final code review of ALL changes on this branch.
Run \`git diff main...HEAD\` (or the base branch) to see the full diff.
Review for: correctness bugs, dead code, missing error handling, security issues.
This review covers ALL tasks collectively.`,
      agentOpts('gate-6-final-review', 'Gates', GATE_RESULT),
    )
    passed = review.passed
    detail = review.detail || ''

    while (!passed && iters < GATE_RETRIES) {
      await agent(
        `Fix these final review issues: ${detail}
Minimal fixes — do not refactor.
Return a concise text summary after writing the file.`,
        { label: `fix-final-r${iters + 1}`, phase: 'Gates', ...(model_tasks ? { model: model_tasks } : {}) },
      )
      const re = await agent(
        'Re-review: verify previous issues fixed. No new issues.',
        agentOpts(`gate-6-r${iters + 1}`, 'Gates', GATE_RESULT),
      )
      passed = re.passed
      if (!passed) {
        lastFailure = re.detail
        lastFix = re.fix_applied || ''
      }
      detail = passed ? 'Final review passed' : (re.detail || detail)
      iters++
    }
  }

  await recordGate(GATE_FINAL_REVIEW, passed, detail, {
    iterations: iters + (executeHadFinalReview ? 1 : 0),
    last_failure: lastFailure,
    last_fix: lastFix,
    next_action: passed ? 'proceed' : 'fix_final_review_issues',
    fix_applied: iters > 0 ? `${iters} fix rounds` : '',
  })
  log(`Gate 6 (final_review): ${passed ? 'PASSED' : `FAILED after ${iters} fix rounds`}`)
} else {
  await recordGate(GATE_FINAL_REVIEW, false, 'Skipped — spec_verified not passed', { iterations: 0, next_action: 'unblock_gate_5' })
  log('Gate 6 (final_review): SKIPPED — gate 5 not passed')
}

// ── Gate 7: git_clean (workflow-owned temp cleanup only) ────────────
if (isGateAlreadyPassed(GATE_GIT_CLEAN, 6)) {
  gateStates[GATE_GIT_CLEAN] = resumeGateStates[GATE_GIT_CLEAN]
  gateCursor = 7
  log('Gate 7 (git_clean): SKIPPED — already passed')
} else if (priorGatePassed()) {
  let passed = false
  let detail = ''
  let iters = 0

  // Clean workflow-owned temp files only (evidence_dir, audit_dir temp files)
  const cleanedPaths = []
  if (evidence_dir) {
    cleanedPaths.push(evidence_dir)
  }

  const r = await agent(
    `Run \`git status --porcelain\` to check working tree cleanliness.
This is a validation-only check for the pipeline — do NOT commit anything.
If there are uncommitted changes, report them but do NOT commit.
If clean: report passed.
If dirty: list the dirty files. The pipeline does not require commits.`,
    agentOpts('gate-7-git-clean', 'Gates', GATE_RESULT),
  )
  passed = r.passed
  detail = r.detail

  await recordGate(GATE_GIT_CLEAN, passed, detail, {
    iterations: 1,
    last_failure: passed ? null : detail,
    evidence_paths: cleanedPaths,
    next_action: passed ? 'done' : 'resolve_dirty_files',
    fix_applied: '',
  })
  log(`Gate 7 (git_clean): ${passed ? 'PASSED' : 'FAILED'}`)
} else {
  await recordGate(GATE_GIT_CLEAN, false, 'Skipped — final_review not passed', { iterations: 0, next_action: 'unblock_gate_6' })
  log('Gate 7 (git_clean): SKIPPED — gate 6 not passed')
}

// Build the gates array from gateStates
const gates = GATE_NAMES.map(name => gateStates[name] || makeGateRecord(name, false, 'Skipped'))

// ── Finalize state and return ───────────────────────────────────────────────────────────────────────────────\n
const finalResumeCursor = {
  phase: gates.every(g => g.passed) ? 'finalize' : 'gates',
  gate_cursor: gateCursor,
  gate_states: gateStates,
  spec_path: spec.spec_path,
  plan_path: planResult.plan_path,
  design: designContext,
}

await flowState('update', {
  phase: 'finalize',
  status: gates.every(g => g.passed) ? 'DONE' : 'BLOCKED_ESCALATING',
  resume_cursor: finalResumeCursor,
  progress: { gates_passed: gates.filter(g => g.passed).length, gates_total: 7 },
})
await flowState('event', { type: 'run_complete', all_passed: gates.every(g => g.passed) })
auditEvents.push({ phase: 'finalize', event: 'run_complete', all_passed: gates.every(g => g.passed) })

return {
  spec: { path: spec.spec_path, review_passed: specReview.passed },
  plan: { path: planResult.plan_path, review_passed: planReview.passed, task_count: planResult.task_count },
  execute: executeResult,
  gates,
  all_passed: gates.every(g => g.passed),
  state_file: state_file || null,
  audit_events: auditEvents,
  evidence_dir: evidence_dir || null,
  resume_cursor: finalResumeCursor,
  design: designContext,
}

