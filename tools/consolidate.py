"""Build consolidated full-auto-pipeline.workflow.js from the three workflow files."""
import os, re, sys

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(f'{base}/skills/auto-mode/workflows/full-auto-pipeline.workflow.js', 'r', encoding='utf-8') as f:
    full_auto = f.read()
with open(f'{base}/skills/auto-mode/workflows/execute-plan.workflow.js', 'r', encoding='utf-8') as f:
    exec_plan = f.read()

# ---- 1. Fix header comment ----
full_auto = full_auto.replace(
    "execute (delegates to execute-plan workflow) → 7 gates.",
    "execute → gates."
)
full_auto = full_auto.replace(
    "// Delegates to execute-plan.workflow.js via workflow() at the Execute phase.\n",
    ""
)

# ---- 2. Remove flow_state_script_path from args_schema ----
full_auto = full_auto.replace(
    "    flow_state_script_path: { type: 'string', description: 'Path to flow-state-adapter.workflow.js' },\n",
    ""
)

# ---- 3. Remove execute_plan_script_path and flow_state_script_path from args ----
full_auto = full_auto.replace(
    "  execute_plan_script_path,\n",
    ""
)
full_auto = full_auto.replace(
    "  flow_state_script_path,\n",
    ""
)

# ---- 4. Replace flowState() function ----
old_flow = re.compile(
    r"let currentRevision = \(resume_from && resume_from\.revision\) \|\| 0\n"
    r"const flowStateScriptPath = flow_state_script_path \|\| null\n"
    r"const flowStateCliPath = flow_state_cli_path \|\| null\n"
    r"\n"
    r"async function flowState\(cmd, payload\) \{.*?\n\}",
    re.DOTALL
)

new_flow = """let currentRevision = (resume_from && resume_from.revision) || 0
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
    `Run the flow-state CLI and return its JSON stdout exactly as structured data.\\n\\nCLI path: ${flowStateCliPath}\\nArguments JSON: ${JSON.stringify(argv)}\\n\\nUse Python to execute the CLI with these arguments. Do not edit files except through the CLI. If the command fails, return ok=false with errors from stdout/stderr.`,
    { label: `flow-state:${cmd}`, schema: FLOW_STATE_RESULT },
  )
  if (result && result.ok && typeof result.revision === 'number') {
    currentRevision = result.revision
  }
  return result || { ok: false, errors: ['flowState returned no result'] }
}"""

full_auto = old_flow.sub(new_flow, full_auto)

# ---- 5. Extract execute-plan unique code ----
ep_lines = exec_plan.split('\n')

# Find start: "function asArray"
start_idx = None
for i, line in enumerate(ep_lines):
    if line.startswith('function asArray'):
        start_idx = i
        break
if start_idx is None:
    print("ERROR: Could not find function asArray in execute-plan")
    sys.exit(1)

# Find end: the closing brace of classifyTaskResult
end_idx = None
brace_count = 0
found_classify = False
for i in range(start_idx, len(ep_lines)):
    if 'function classifyTaskResult' in ep_lines[i]:
        found_classify = True
    if found_classify:
        brace_count += ep_lines[i].count('{') - ep_lines[i].count('}')
        if brace_count == 0 and found_classify:
            end_idx = i + 1
            break
if end_idx is None:
    print("ERROR: Could not find end of classifyTaskResult")
    sys.exit(1)

execute_helpers = '\n'.join(ep_lines[start_idx:end_idx])

# Replace references in execute helpers
execute_helpers = execute_helpers.replace('workflowArgs', 'args')
execute_helpers = re.sub(r'\bopts\(', 'agentOpts(', execute_helpers)

# Get main execution body (from "const partitions =" to end of file)
main_body_start = None
for i, line in enumerate(ep_lines):
    if line.startswith('const partitions = {'):
        main_body_start = i
        break
if main_body_start is None:
    print("ERROR: Could not find const partitions in execute-plan")
    sys.exit(1)

main_body = '\n'.join(ep_lines[main_body_start:])
main_body = main_body.replace('workflowArgs', 'args')
main_body = re.sub(r'\bopts\(', 'agentOpts(', main_body)

# ---- 6. Insert execute-plan helpers before the Scope phase ----
scope_marker = "// ── Phase 1: Scope"
scope_idx = full_auto.find(scope_marker)
if scope_idx == -1:
    print("ERROR: Could not find Scope phase marker")
    sys.exit(1)

insert_block = "\n// ── Execute-phase helpers (merged from execute-plan) ────────────────────────\n\nconst COMMAND_EXECUTION_PRIMITIVE = 'workflow_agent_only'\nconst ENFORCEMENT_MODE = 'prompt_only'\n\n" + execute_helpers + "\n\n"

full_auto = full_auto[:scope_idx] + insert_block + full_auto[scope_idx:]

# ---- 7. Replace the workflow() delegation with inline execution ----
old_execute_pattern = re.compile(
    r"// ── Phase 8: Execute.*?// end execute skip guard",
    re.DOTALL
)

new_execute = (
    "// ── Phase 8: Execute ───────────────────────────────────────────\n"
    "// Inlined execute-plan: implement → spec review → code review → final review\n"
    "\n"
    "if (shouldSkipPhase('execute')) {\n"
    "  log('Phase: Execute — SKIPPED (resume)')\n"
    "  auditEvents.push({ phase: 'execute', event: 'phase_skipped', reason: 'resume' })\n"
    "} else {\n"
    "phase('Execute')\n"
    "await flowState('event', { type: 'phase_start', phase: 'execute' })\n"
    "log('Starting execute phase...')\n"
    "\n"
    "// Execute-phase local variables\n"
    "const MAX_RETRIES = RETRIES\n"
    "const resumeState = normalizeResumeState(resume_from || {})\n"
    "const result_replay = resumeTaskReplay || []\n"
    "\n"
    + main_body +
    "\n"
    "log(`Execute: ${executeResult.completed.length} completed, ${executeResult.blocked.length} blocked`)\n"
    "await flowState('update', { phase: 'execute',\n"
    "  progress: { tasks_passed: executeResult.completed.length,\n"
    "    tasks_total: executeResult.completed.length + executeResult.blocked.length } })\n"
    "auditEvents.push({ phase: 'execute', event: 'phase_complete',\n"
    "  completed: executeResult.completed.length, blocked: executeResult.blocked.length })\n"
    "} // end execute skip guard"
)

full_auto = old_execute_pattern.sub(new_execute, full_auto)

# ---- 8. Write result ----
with open(f'{base}/skills/auto-mode/workflows/full-auto-pipeline.workflow.js', 'w', encoding='utf-8') as f:
    f.write(full_auto)

print(f"Written {len(full_auto)} chars, {full_auto.count(chr(10))} lines")
