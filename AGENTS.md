# Agents

Model-tiered agent pipeline. Agent definitions live in `agents/*.md`; gate order and scheduling live in `skills/dev-orchestrator/references/pipeline-operations.md`.

## Source of Truth

- Agent behavior lives in `agents/*.md`.
- Gate ordering, scheduling, review, and acceptance live in `skills/dev-orchestrator/references/pipeline-operations.md`.
- Review command boundaries, sentinel inputs, and fix loops live in `skills/dev-orchestrator/references/review.md`.
- Diagnostic command data sources and output rules live in `skills/dev-orchestrator/references/diagnostics.md`.
- Hook registration lives in `scripts/render-hooks.py`; committed host manifests are generated snapshots.
- `commands/*.md` are thin entry points and should not duplicate the full pipeline checklist.

Use `workflow-intake` before planning when a task references another repo/plugin/workflow. External sources are inspiration, not authority; do not import a second agent or command system wholesale.

Use `dev-orchestrator` after planning, approval, or any multi-step/cross-file implementation request. It coordinates the agent pipeline rather than becoming a separate agent.

Research is dispatched as general-purpose subagents using the `research` skill methodology. **Never use `subagent_type: "claude-code-flow:research"`; always use `subagent_type: "general-purpose"`.**
