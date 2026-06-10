// Invoked by the auto-mode dynamic workflow via:
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

const workflowArgs = typeof args === 'undefined' ? {} : args
const { groups, tasks, worktree, model_tasks } = workflowArgs
const result_replay = workflowArgs.result_replay || []
const MAX_RETRIES = 5
const COMMAND_EXECUTION_PRIMITIVE = 'workflow_agent_only'
const ENFORCEMENT_MODE = 'prompt_only'

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
  const anchor = resolveDiffAnchors(workflowArgs, task, impl, stage)
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
        captureAttemptBase(workflowArgs, task, task, label)
        result = await agent(implementPrompt(task),
          opts(label, 'Implement', IMPLEMENT_RESULT))
        recordAttemptDiffEvidence(workflowArgs, task, task, label)
      } else if (rung === 'self_service_retry') {
        label = 'escalate-self-service:' + task.id
        captureAttemptBase(workflowArgs, task, task, label)
        result = await agent(selfServicePrompt(task),
          opts(label, 'Implement', IMPLEMENT_RESULT))
        recordAttemptDiffEvidence(workflowArgs, task, task, label)
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

const REVIEW_REREVIEW_RESULT = {
  ...REVIEW_RESULT,
  required: [
    'passed', 'issues', 'summary',
    'prior_findings_verified', 'unresolved_issue_ids', 'new_issues',
    'diff_verified', 'targeted_verification_credible', 'scope_concerns',
  ],
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
  const anchor = resolveDiffAnchors(workflowArgs, task, impl, stage)
  const evidence = latestDiffEvidence(impl, task) || collectDiffEvidence(anchor)
  return '\n\n## Controller Diff Evidence\n\n' + JSON.stringify(evidence, null, 2) + '\n\n' +
    (evidence.diff_verified ? 'diff_verified=true. Review this verified diff first.\n' : 'diff_verified=false. State this limitation; files_modified is untrusted; do not expand scope beyond available evidence unless needed.\n') +
    diffAnchorPrompt(task, impl, stage)
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
      diff_anchor: resolveDiffAnchors(workflowArgs, task || {}, impl || {}, stage || 'fix'),
      latest_diff_evidence: latestDiffEvidence(impl, task) || collectDiffEvidence(resolveDiffAnchors(workflowArgs, task || {}, impl || {}, stage || 'fix')),
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
        iterations: ctx._iterations_spec || 0,
        evidence: extractEvidence(task, ctx.impl, ctx.spec_review, null),
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
        iterations: ctx._iterations_code || 0,
        evidence: extractEvidence(task, ctx.impl, ctx.spec_review, ctx.code_review),
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
          captureAttemptBase(workflowArgs, t, t, attemptLabel)
          let result = await agentWithSchemaRetry(
            implementPrompt(t),
            opts(attemptLabel, 'Implement', IMPLEMENT_RESULT),
            ESCALATION_ATTEMPTS.schema_retry,
          )
          recordAttemptDiffEvidence(workflowArgs, t, t, attemptLabel)

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
            opts('spec-review:' + id, 'Spec Review', REVIEW_RESULT),
            0,
          )
          review = normalizeReviewResult(review, 'spec_review', id, null)

          let iterations = 0
          const hasBlocking = () => hasBlockingIssues(review, 'spec_review', risk)

          while (review && hasBlocking() && iterations < MAX_RETRIES) {
            const blockingIssues = review.issues.filter(i =>
              isIssueBlocking('spec_review', risk, i.severity, i.blocking)
            )
            log(id + ': spec review found ' + blockingIssues.length + ' blocking issue(s) — fixing')
            const fixLabel = 'fix-spec:' + id + '-r' + (iterations + 1)
            captureAttemptBase(workflowArgs, ctx, ctx, fixLabel)
            const updated = await agentWithSchemaRetry(
              fixPrompt(blockingIssues, impl.files_modified, ctx, impl, 'spec_fix', iterations + 1),
              opts(fixLabel, 'Spec Review', FIX_RESULT),
              0,
            )
            recordAttemptDiffEvidence(workflowArgs, ctx, ctx, fixLabel)
            if (updated) ctx.impl = { ...ctx.impl, ...updated }
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
              opts('spec-review:' + id + '-r' + (iterations + 1), 'Spec Review', REVIEW_REREVIEW_RESULT),
              0,
            )
            review = normalizeReviewResult(review, 'spec_review', id, priorSpecReview)
            iterations++
          }

          const specPassed = review ? !hasBlocking() : false
          const exhausted = iterations >= MAX_RETRIES && !specPassed

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
            opts('code-review:' + ctx.id, 'Code Review', REVIEW_RESULT),
            0,
          )
          review = normalizeReviewResult(review, 'code_review', ctx.id, ctx.spec_review)

          let iterations = 0
          const hasBlocking = () => hasBlockingIssues(review, 'code_review', risk)

          while (review && hasBlocking() && iterations < MAX_RETRIES) {
            const blockingIssues = review.issues.filter(i =>
              isIssueBlocking('code_review', risk, i.severity, i.blocking)
            )
            log(ctx.id + ': code review found ' + blockingIssues.length + ' blocking issue(s) — fixing')
            const fixLabel = 'fix-code:' + ctx.id + '-r' + (iterations + 1)
            captureAttemptBase(workflowArgs, ctx, ctx, fixLabel)
            const updated = await agentWithSchemaRetry(
              fixPrompt(blockingIssues, ctx.impl.files_modified, ctx, ctx.impl, 'code_fix', iterations + 1),
              opts(fixLabel, 'Code Review', FIX_RESULT),
              0,
            )
            recordAttemptDiffEvidence(workflowArgs, ctx, ctx, fixLabel)
            if (updated) ctx.impl = { ...ctx.impl, ...updated }

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
              opts('code-review:' + ctx.id + '-r' + (iterations + 1), 'Code Review', REVIEW_REREVIEW_RESULT),
              0,
            )
            review = normalizeReviewResult(review, 'code_review', ctx.id, priorCodeReview)
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
      { id: 'final', description: 'Final review for ' + allIds, attempt_diff_evidence: partitions.completed.flatMap(e => e.attempt_diff_evidence || []) },
    ),
    opts('final-review', 'Final Review', REVIEW_RESULT),
  )
  finalReview = normalizeReviewResult(finalReview, 'final_review', 'final', null)
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

