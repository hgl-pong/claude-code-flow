# Code Quality Reviewer Prompt Template

Use this template when dispatching a code quality reviewer subagent.

**Purpose:** Verify implementation is well-built (clean, tested, maintainable)

**Only dispatch after spec compliance review passes.**

```
Task tool (general-purpose):
  Review the verified controller diff before any other source.

  DESCRIPTION: [task summary, from implementer's report]
  PLAN_OR_REQUIREMENTS: Task N from [plan-file]
  DIFF_METADATA: [controller diff metadata]
  VERIFIED_DIFF: [diff summary/body when diff_verified=true]
```

**Diff-first rules:**
- Inspect controller diff metadata first.
- Treat `files_modified` as untrusted unless controller diff confirms it.
- If `diff_verified=false`, report that limitation and do not claim full diff coverage.
- Do not run conflicting scope unless needed to resolve unclear/missing diff evidence.
- Preserve role boundaries; do not duplicate spec-review findings unless unresolved.
- Require issue file/line where available; include `location_unavailable_reason` when omitted.
- Preserve `prior_issue_id` for unresolved carried-forward findings.

**In addition to standard code quality concerns, the reviewer should check:**
- Does each file have one clear responsibility with a well-defined interface?
- Are units decomposed so they can be understood and tested independently?
- Is the implementation following the file structure from the plan?
- Did this implementation create new files that are already large, or significantly grow existing files? (Don't flag pre-existing file sizes — focus on what this change contributed.)

**For 2D game work, also check:**
- simulation and renderer responsibilities are separated.
- Phaser scenes orchestrate rendering/input but do not own gameplay rules.
- DOM HUD/menu surfaces are used for dense text and accessibility-sensitive controls.
- Asset references stay behind a stable asset manifest.
- Sprite/image generation is delegated to claude-code-flow:image-generation, not a duplicate provider path.
- playtest/smoke evidence exists for runnable game changes, or unverifiable runtime acceptance is called out.

**Code reviewer returns:** Strengths, Issues (Critical/Important/Minor), Assessment, diff_verified limitation when applicable. Free-form severity/category/location values are accepted and normalized by the workflow.
