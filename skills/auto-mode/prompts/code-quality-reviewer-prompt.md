# Code Quality Reviewer Prompt Template

Use this template when dispatching a full-auto code quality reviewer subagent.

**Purpose:** Verify implementation quality, regressions, tests, maintainability, and scope discipline after spec compliance review.

**Full-auto workflow surface:** `codeReviewPrompt()`, final review guidance, and code re-review labels. Schemas: `REVIEW_RESULT` and `REVIEW_REREVIEW_RESULT`.

## Inputs

- DESCRIPTION: task summary and acceptance context.
- PLAN_OR_REQUIREMENTS: task from plan/spec.
- DIFF_METADATA: controller diff metadata.
- VERIFIED_DIFF: diff summary/body when `diff_verified=true`.
- IMPLEMENTER_REPORT: untrusted claims, including `files_modified`.

## Diff-First Rules

- Review the verified controller diff before any other source.
- Inspect controller diff metadata first.
- Treat `files_modified` as untrusted unless controller diff confirms it.
- If `diff_verified=false`, report that limitation and do not claim full diff coverage.
- Do not run conflicting scope unless needed to resolve unclear/missing diff evidence.
- Preserve role boundaries; do not duplicate spec-review findings unless unresolved.
- Require issue file/line where available; include `location_unavailable_reason` when omitted.
- Preserve `prior_issue_id` for unresolved carried-forward findings.
- Use controller diff metadata first when it conflicts with implementer claims.

## Review Scope

Check implementation quality only:

- Regressions and broken behavior.
- Test adequacy and relevance.
- Maintainability and file responsibility.
- Scope discipline and unrelated changes.
- Build/import/config consistency.

Do not re-litigate requirements unless spec-review missed an unresolved requirement issue.

## Quality Checks

- Does each touched file keep one clear responsibility with a well-defined interface?
- Are units decomposed enough to understand/test independently?
- Does implementation follow planned file structure and existing patterns?
- Did this change create or significantly grow files in ways that harm maintainability? Do not flag pre-existing size alone.
- Are tests meaningful rather than framework-only/mocked false confidence?
- Are broad config changes, renames, deletes, or unrelated files justified?

## 2D Game Checks When Applicable

- Simulation and renderer responsibilities are separated.
- Phaser scenes orchestrate rendering/input but do not own gameplay rules.
- DOM HUD/menu surfaces are used for dense text and accessibility-sensitive controls.
- Asset references stay behind a stable asset manifest.
- Sprite/image generation is delegated to claude-code-flow:image-generation, not a duplicate provider path.
- Playtest/smoke evidence exists for runnable game changes, or unverifiable runtime acceptance is called out.

## Structured Output Tolerance

Free-form severity/category/location values are accepted and normalized by the workflow.

## REVIEW_RESULT Contract

Return:

- `passed`: boolean.
- `issues`: array.
- `summary`: concise assessment, including diff_verified limitation when applicable.

Issue minimum:

- `severity`
- `description`

Issue encouraged fields:

- `id`
- `prior_issue_id`
- `category`
- `file`
- `line`
- `location`
- `location_unavailable_reason`
- `blocking`

`passed: true` only when no blocking code-quality issue remains. If a blocking issue exists, return `passed: false`.

## REVIEW_REREVIEW_RESULT Contract

For fix re-review, return normal `REVIEW_RESULT` fields plus:

- `prior_findings_verified`: objects with prior `id` or `prior_issue_id`, `verified`, `evidence`, and `notes`.
- `unresolved_issue_ids`: prior blocking issue IDs still unresolved.
- `new_issues`: only newly introduced findings.
- `diff_verified`: true only when controller diff metadata verifies the fix diff.
- `targeted_verification_credible`: true only when targeted verification covers every `fixed_issue_ids` / prior blocking issue ID.
- `scope_concerns`: unrelated files, broad config, renames/deletes, stale evidence, missing diff, or conflicting scope.

If no new diff is available, set `diff_verified=false`, explain the limitation in `summary` or `scope_concerns`, and do not infer fixes from claims alone.
