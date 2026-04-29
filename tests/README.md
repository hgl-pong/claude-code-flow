# Tests

Fast local regression tests for the plugin structure and hook behavior.

Run:

```bash
python tests/run-tests.py
```

These tests intentionally avoid Claude CLI or network dependencies. They cover:

- Plugin and hook JSON parsing
- Agent, command, and skill frontmatter
- Hook command references
- Python hook syntax
- Shell script LF line endings for bash compatibility
- Verification evidence tracking
- Flow state default merging
- Metrics aggregation for verification evidence

## Claude Code E2E

Slow optional tests that invoke Claude Code headless with `claude -p`:

```bash
bash tests/claude-code/run-e2e-tests.sh
```

Run one test:

```bash
bash tests/claude-code/run-e2e-tests.sh --test test-workflow-skills.sh
```

These require:

- Claude Code CLI installed and authenticated
- This plugin available to the Claude Code session
- Network/model access

The runner performs a short Claude preflight. If the CLI exists but the model/API is unavailable, it reports the E2E suite as skipped instead of burning time on every test.

The E2E layer covers:

- Claude can explain the workflow skills
- Claude can explain the command flow and ordering
- Claude can run the local regression test command through Bash
