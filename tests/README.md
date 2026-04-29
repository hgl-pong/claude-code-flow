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

Optional tests that invoke Claude Code headless (`claude -p`).

### Fast tests (~2-5 min each, default)

```bash
bash tests/claude-code/run-e2e-tests.sh
```

Run one test:

```bash
bash tests/claude-code/run-e2e-tests.sh --test test-skill-brainstorming.sh
```

Run with verbose output:

```bash
bash tests/claude-code/run-e2e-tests.sh --verbose
```

### Integration tests (10-30 min, costs real tokens)

```bash
bash tests/claude-code/run-e2e-tests.sh --integration
```

### Skill-triggering tests

Verify that natural-language prompts cause Claude to auto-load the right skill:

```bash
bash tests/skill-triggering/run-all.sh
bash tests/skill-triggering/run-all.sh --skill brainstorming
```

### Requirements

- Claude Code CLI installed and authenticated
- This plugin available to the Claude Code session
- Network/model access

The runner performs a short Claude preflight. If the CLI exists but the model/API is
unavailable, it reports the E2E suite as skipped instead of burning time on every test.

### Fast test coverage

| Test file | What it verifies |
|---|---|
| `test-workflow-skills.sh` | Claude explains all 6 workflow skills |
| `test-workflow-commands.sh` | Claude explains all 6 slash commands + ordering |
| `test-local-regression-via-claude.sh` | Claude runs `python tests/run-tests.py` via Bash |
| `test-skill-using-claude-code-flow.sh` | Skill-selection-first gate, companion skills, workflow order |
| `test-skill-brainstorming.sh` | Diverge/converge, approval gate, output artifact |
| `test-skill-writing-plans.sh` | Test-first, atomic tasks, verification step per task |
| `test-skill-testing-strategy.sh` | RED→GREEN→REFACTOR, test pyramid, mocking policy |
| `test-skill-systematic-debugging.sh` | Reproduce first, hypothesis, root cause, bisect |
| `test-skill-verification-before-completion.sh` | Fresh evidence, mandatory checklist, no claimed success |
| `test-skill-dev-orchestrator.sh` | Agent roster, mode selection, review/acceptance gates |

### Integration test coverage

| Test file | What it verifies |
|---|---|
| `test-integration-dev-orchestrator.sh` | Full plan execution: skill invoked, subagents dispatched, files created, tests pass, git commits made, token usage reported |

### Token analysis

After any integration test (or any session), analyze token usage:

```bash
python3 tests/claude-code/analyze-token-usage.py ~/.claude/projects/<encoded-path>/<session-id>.jsonl
```
