# Workflow Engine

Internal Dynamic Workflow engine used by `auto-mode` and `semi-auto`. Not a user-facing skill.

## Boundary

```
Workflow({ scriptPath: '<execute-plan.workflow.js>' }, args) → result
```

`execute-plan` args: `{ groups, tasks, worktree, model_tasks }`.

`full-auto-pipeline` args: `{ task, worktree, specs_dir, plans_dir, execute_plan_script_path, model_tasks, max_retries, state_file, audit_dir, evidence_dir, resume_from, retry_policy, allowed_escalation_models, allow_commit, flow_state_script_path }`.

## Controller Steps

1. **Prepare context** — read plan, extract tasks, build dependency graph.
2. **Build args** — construct `groups`, `tasks`, `worktree`, `model_tasks`.
3. **Launch** — call `Workflow()` once.
4. **Handle results** — inspect result partitions, evidence, and final review.

Task metadata fields:

| Field | Required | Default / Values |
|---|---|---|
| `id` | yes | string |
| `description` | yes | full plan text |
| `depends_on` | no | `[]` |
| `files` | no | `[]` |
| `tests` | no | `[]` |
| `verification` | no | `[]` |
| `acceptance_refs` | no | `[]` |
| `runtime_evidence_required` | no | `required` / `optional` / `not_needed`; default `optional` |
| `risk` | no | `low` / `medium` / `high` / `critical`; default `medium` |
| `subsystem` | no | `unknown` |

High/critical tasks require `files`, `tests`, `verification`. `runtime_evidence_required: required` requires `verification` and `acceptance_refs`.

## Results Contract

Reviewers verify independently and treat reports as potentially incomplete or optimistic.

Each task appears in exactly one canonical partition; `results.completed[]` is alias/backward compatibility for `results.passed[]`.

- `results.passed[]`: `id`, `spec_passed`, `code_passed`, `code_review`, `files`, `evidence`.
- `results.completed[]`: same IDs as `passed`; alias.
- `results.blocked[]`: `id`, `reason`, `classification`, `impl`.
- `results.stalled[]`: `id`, `stage`, `evidence`.
- `results.failed_review[]`: `id`, `stage` (`spec_review`/`code_review`), `blocking_issues`, `iterations`, `evidence`.
- `results.needs_escalation[]`: `id`, `reason`, `classification`, `rung_reached`, `impl`.
- `results.final_review`: fix Critical/High/Important before finishing.

If all tasks are `passed` and final review has no blocking issues → use `claude-code-flow:finishing-a-development-branch`.

## Blocking / Retry Contract

Blocker taxonomy: `agent_output_invalid`, `merge_conflict`, `permissions`, `external_service`, `tooling_unavailable`, `test_failure`, `runtime_failure`, `dependency_failure`, `architecture_decision`, `scope_too_large`, `missing_context`.

Escalation ladder: `schema_retry` → `self_service_retry` → `stronger_model` → `split_subtask` → `enriched_context` → `ask_user`.

For returned blocked/escalated tasks: re-dispatch with a more capable model / better model, split oversized work, or escalate to human partner when the plan is wrong / needs plan-level decision. Never re-dispatch with the same model and same instructions; never manually implement blocked tasks in main session.

## Review Threshold

Spec Review and Code Review:

| Risk | Critical | High | Important | Minor | Info |
|---|---|---|---|---|---|
| `low` | BLOCKS | BLOCKS | if_explicit | no | no |
| `medium` | BLOCKS | BLOCKS | BLOCKS | no | no |
| `high` | BLOCKS | BLOCKS | if_explicit | no | no |
| `critical` | BLOCKS | BLOCKS | BLOCKS | BLOCKS | no |

Final Review: Critical/High/Important BLOCK; Minor/Info do not. `if_explicit` blocks only when reviewer sets `blocking=true`.

Task statuses: `queued`, `implementing`, `implemented`, `spec_reviewing`, `code_reviewing`, `passed`, `blocked`, `stalled`, `failed_review`, `failed`, `split`.

Implementer statuses: `DONE` → spec review; `DONE_WITH_CONCERNS` → concerns feed review; `BLOCKED` → escalation ladder. Review retry loops allow up to 5 iterations.

## Full-Auto Gates / Evidence

Gate predicates:

| Gate | Predicate |
|---|---|
| `tasks_executed` | no blocked tasks |
| `reviews_passed` | every completed task has `code_passed === true` |
| `tests_pass` | project test command exits 0 |
| `runtime_evidence` | build/run smoke succeeds or unverifiable reason recorded |
| `spec_verified` | requirements checked against code |
| `final_review` | cross-task review approved |
| `git_clean` | `git status --porcelain` empty |

Runtime evidence manifest fields: `commands`, `exit_codes`, `logs`, `screenshots`, `artifacts`, `crash`, `hang`, `unverified_acceptance_items`, `blocking_risks`, `generated_at`.
Task evidence fields: `commit_sha`, `test_results`, `verification_commands`, `evidence_paths`, `concerns`, `files_modified`.
Gate 7 (`git_clean`) is validation-only and does NOT instruct commits. Commits happen during execution.

## Model Selection

`model_tasks`: `null` uses session model. Available workflow agent models: forge, oracle, prism, artist. Use forge/Sonnet for full-stack/UI/multi-file; oracle/Opus for planning/architecture; prism/Sonnet for verification; artist/Sonnet for image work; default for mechanical 1-2 file tasks.

## UI / Games / Images

Visible UI: read root `DESIGN.md` and include relevant design text in task description.

2D browser games: default Phaser unless spec says otherwise. Use `references/2d-game-workflow.md`. Preserve: simulation outside renderer, thin scenes, DOM HUD, camera model, input action map, stable asset manifest, browser smoke/playtest evidence. Terms: Phaser, simulation, renderer, DOM, sprite, image-generation, playtest.

Image generation and image editing: route through `claude-code-flow:image-generation`; artist agents follow `artist-prompt.md`; consume manifests only after files exist.

## Commit Policy

- Commits are normal git commits; user can revert/reset.
- No automatic PR creation. PRs belong to finishing skill only if requested.
- Gate 7 validates clean state; it does not commit.
- `allow_commit` controls pipeline commits; default `true`.

## Red Flags

Never: implement on main/master without explicit consent; skip plan read; make workflow read plan files; edit workflow scripts at launch; ignore blocked tasks; proceed with blocking final-review issues; cancel mid-workflow; manually implement blocked tasks.

Always: build dependency graph; include full task descriptions; include `DESIGN.md` content for UI; inspect blocked tasks after completion; finish only after all pass.
