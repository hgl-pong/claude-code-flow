export const meta = {
  name: 'flow-state-adapter',
  description: 'Bridge workflow state updates to hooks/scripts/flow-state.py CLI',
  phases: [{ title: 'Write State' }],
}

const {
  command,
  state_file,
  payload_json,
  expected_revision,
  flow_state_cli_path,
} = args

phase('Write State')

const FLOW_STATE_RESULT = {
  type: 'object',
  additionalProperties: true,
  properties: {
    ok: { type: 'boolean' },
    revision: { type: 'number' },
    errors: { type: 'array', items: { type: 'string' } },
  },
  required: ['ok'],
}

const payload = payload_json ? JSON.parse(payload_json) : {}
let argv = []

if (command === 'update') {
  argv = ['update', '--state-file', state_file, '--patch-json', JSON.stringify(payload)]
  if (expected_revision !== null && expected_revision !== undefined) {
    argv.push('--expected-revision', String(expected_revision))
  }
} else if (command === 'event') {
  const { type, ...data } = payload
  argv = ['event', '--state-file', state_file, '--type', type || 'event', '--json-data', JSON.stringify(data)]
} else if (command === 'manifest') {
  argv = ['manifest', '--state-file', state_file, '--patch-json', JSON.stringify(payload)]
} else if (command === 'resume') {
  argv = ['resume', '--state-file', state_file]
} else if (command === 'validate') {
  argv = ['validate', '--state-file', state_file]
} else if (command === 'snapshot') {
  argv = ['snapshot', '--state-file', state_file, '--reason', payload.reason || 'workflow']
} else {
  return { ok: false, errors: [`Unsupported flow-state command: ${command}`] }
}

return await agent(
  `Run the flow-state CLI and return its JSON stdout exactly as structured data.\n\nCLI path: ${flow_state_cli_path || 'hooks/scripts/flow-state.py'}\nArguments JSON: ${JSON.stringify(argv)}\n\nUse Python to execute the CLI with these arguments. Do not edit files except through the CLI. If the command fails, return ok=false with errors from stdout/stderr.`,
  { label: `flow-state:${command}`, phase: 'Write State', schema: FLOW_STATE_RESULT },
)
