---
name: Workflow Intake
version: "1.0.0"
description: "Use when a task asks to reference, borrow from, port, import, or optimize this workflow using another repository, plugin, agent pack, or external workflow."
argument-hint: "<source repo or workflow idea>"
---

# Workflow Intake

Selectively adapt outside workflow ideas into Claude Code Flow without importing a second workflow system.

## Trigger

Use this skill before planning when the task includes any of:

- "reference this repo", "inspired by", "borrow from", "compare with"
- "port", "import", "copy", "bring in", "migrate"
- "optimize the workflow", "improve agents/skills/hooks/commands"
- A URL or local path that points to another agent/workflow collection

## Iron Law

**Do not wholesale-import external workflow surfaces.** Every candidate must either strengthen an existing Claude Code Flow lane, become a small native addition, or be rejected with a reason.

## Intake Decision Record

Create or update `<output_dir>/intake-decision.md` when the intake affects planning. The record must include:

`<output_dir>` resolves to the active workflow plan directory, normally `.claude/flow/plans/<slug>/`.

```markdown
# Intake Decision

## Source
- Repository/path:
- Date inspected:
- Scope inspected:

## Fit Criteria
- Strengthens an existing gate/skill/command:
- No duplicate agent taxonomy:
- No external runtime dependency:
- Fits plugin install/runtime constraints:
- Testable in this repo:

## Candidates
| Candidate | Source idea | Adopt / Adapt / Reject / Defer | Target surface | Reason |
|---|---|---|---|---|

## Rejections
List rejected ideas explicitly, especially large agent catalogs, external control planes, duplicated command systems, or project-specific content.

## Handoff
Concrete files/skills/commands/hooks to change in this repo.
```

## Selection Rubric

| Decision | Use When | Required Action |
|---|---|---|
| Adopt | The idea already matches this repo's architecture and needs minimal wording changes | Add to the existing native surface |
| Adapt | The idea is useful but assumes different agents, paths, tools, or runtime | Rewrite into Claude Code Flow terms |
| Reject | The idea duplicates current lanes, adds external runtime assumptions, or conflicts with gates | Record the rejection and do not port it |
| Defer | The idea may be useful but needs a separate design or dependency decision | Record follow-up criteria |

## What Usually Fits

- Better gate checklists, handoff templates, review standards, and verification loops
- Skill placement policy: curated repo skills vs local/generated skills
- Context budget and compacting guidance that works with existing hooks
- Thin command shims that route to maintained skills
- Security or quality reminders that use existing sentinel/prism gates

## What Usually Does Not Fit

- A second agent taxonomy that competes with `oracle`, `forge`, `prism`, and `sentinel`
- Runtime control planes, daemons, or installers not already required by this plugin
- Large language/framework catalogs unless the current repo has an explicit gap
- Project-specific business, ops, or personal workflow content
- Hooks that require new external CLIs without a clear local fallback

## Process

1. Identify the source and limit the inspection scope.
2. Inventory ideas by category: agents, skills, commands, hooks, rules, docs, runtime.
3. Map each useful idea to an existing Claude Code Flow lane first.
4. Reject or defer anything that creates a parallel system.
5. For accepted ideas, choose the smallest repo-native surface:
   - existing skill/reference doc before a new skill
   - thin command before full command body
   - hook only when passive guidance is insufficient
6. Include intake findings in oracle's planning context.
7. Verify with the normal plugin integrity tests.

## Output

- `intake-decision.md` for standard/deep/autonomous tasks
- A concise user-facing summary:
  - ideas adopted
  - ideas adapted
  - ideas rejected
  - files to change
