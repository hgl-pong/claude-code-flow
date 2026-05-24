# Pipeline Operations Reference

Detailed gate specifications, context envelope templates, and scheduling rules for the development pipeline. This reference is the harness control-plane contract: explicit gates, durable state, structured handoffs, hook-enforced policy, and evidence-based completion.

## Policy Trace

Each gate decision must leave a short trace in the active plan or phase context: checked/skipped, reason, owner, and required evidence. Hooks may enforce deterministic policy (routing, dangerous tools, completion blocking), but product judgment stays in the orchestrator/oracle path.

## Mandatory Gate Checklist (Full)

```
GATE CHECKLIST (evaluate for this specific task):

[ ] Gate 1: Brainstorm — mandatory for: new features, behavior changes, UI work,
    architecture changes, broad refactors. Skip only for: narrow bug fixes with
    known root cause, config changes, single-file edits with clear spec.

[ ] Gate 2: Research (general-purpose subagent + research skill) — default-on
    before plan. First classify the request by estimated size. Very lightweight
    tasks may skip research/plan: changing only a few lines, touching 1-2 files,
    or adding 1-2 small files with obvious scope. Heavy tasks MUST use the full
    flow: more than 5 touched files, more than 3 newly created files, broad
    behavior/workflow/prompt/hook/test changes, architecture/UI changes, unfamiliar
    code, or quality-sensitive outcomes. When unsure, classify as heavy enough to
    research and plan.
    Research MUST include local file inspection. Include external research only
    when external facts, library/API behavior, competitive/product comparison, or
    current ecosystem knowledge materially affect the solution, unless the user
    forbids network access or the environment cannot access the network. Produce
    a written research artifact before plan; chat-only synthesis
    is not enough. Strong research is a quality gate: it determines whether the
    final solution is merely functional or competitive.
    **Dispatch with `subagent_type: "general-purpose"` — research is a skill, not
    an agent.** Multiple independent research/product/design streams MAY run in
    parallel. Oracle remains SEQUENTIAL after research — never dispatch oracle
    until required research finishes and findings are available.

[ ] Gate 2a: Reference Intake (workflow-intake skill) — mandatory when the
    user asks to reference, borrow from, port, import, compare with, or optimize
    from another repo/plugin/workflow. Produce `<output_dir>/intake-decision.md`
    before oracle starts. Each source idea must be marked Adopt / Adapt /
    Reject / Defer. Rejected ideas MUST include a reason. Intake is sequential
    with oracle planning and must not introduce a second agent taxonomy, command
    system, hook runtime, or external control plane.

[ ] Gate 3: Plan (oracle) — default-on before implementation. Skip only for
    very lightweight tasks using the size criteria from Gate 2. Oracle/orchestrator MUST
    produce a plan document at `<output_dir>/plan-brief.md` with TaskCreate tasks
    before any forge or direct code edit starts. The plan document MUST include
    Local Research, External Research, Success Criteria, Verification, and Self
    Review Result sections. Oracle MUST receive research findings as input when
    Gate 2 was checked and intake decisions as input when Gate 2a was checked.

[ ] Gate 3a: Plan Review — ALWAYS mandatory (all modes including quick).
    Two-phase review before execution begins:

    Phase 1 — Self Review (oracle/orchestrator):
    a) Every requirement maps to at least one task.
    b) No placeholders, TBDs, or "similar to previous task" shortcuts.
    c) File paths are exact and consistent across tasks.
    d) Test commands are concrete and runnable.
    e) Dependency chain (blockedBy) is correct — no cycles, no false blocks.
    f) No file conflicts between parallel tasks.
    Fix any issues found before proceeding to Phase 2.

    Phase 2 — Human Review:
    Present the plan to the user for approval. No implementation dispatches
    until the user explicitly approves. If the user requests changes, oracle
    revises and both phases repeat.

    After approval, classify execution as very lightweight or agentic. Direct
    main-conversation implementation is allowed only for tasks under the Gate 2
    size thresholds. All other implementation work MUST dispatch bounded
    subagents by role (forge for code, prism for verification, sentinel for review)
    while the main conversation owns decomposition, envelopes, task coordination,
    artifact checks, evidence recording, and final reporting. For long tasks with
    3+ task nodes, multiple dispatch waves, or rolling unblocks, create a harness
    team and use the shared TaskList as the durable coordination surface.

[ ] Gate 4: Architecture (oracle) — see mode table. If mandatory: oracle
    MUST produce design document before implementation.

[ ] Gate 5: UI Research (general-purpose subagent + research skill) — mandatory
    when task domain is frontend-UI AND mode is standard+. Research subagent
    MUST produce ui-research.md with CONCRETE data:
    a) Local codebase: existing components, styling approach (Tailwind/CSS Modules/etc),
       actual CSS variables and font imports in use.
    b) Competitor analysis: 2-3 products — hex values, font names, layout structure,
       spacing density, component personality, NOT vague "uses a nice palette".
    c) Design intelligence: specific font pairings, type scale ratios, color families
       for this domain, grid systems, dark mode strategies.
    Research MUST complete before Gate 6 (UI Design) starts.

[ ] Gate 6: UI Design (ui-design skill) — mandatory when task domain is frontend-UI
    AND mode is standard+. UI design skill MUST produce DESIGN.md following the
    Design Methodology (emotional signature → color roles → type system → icon
    system → spacing rhythm → layout grid → elevation strategy → border radius
    scale → transition tokens → component states). DESIGN.md MUST
    include layout composition plan for page-level designs.

    Gate 6 has mandatory sub-gates:
    6a) Self-Review — run 40+ item checklist, fix all issues.
    6b) Design Viewer — offer user to preview/edit visually (recommended, not mandatory).
    6c) User Review — present DESIGN.md to user, get explicit approval.
    Forge CANNOT be dispatched for UI work until Gate 6c (user approval) passes.

[ ] Gate 7: Review (sentinel) — see mode table. If mandatory: sentinel
    MUST approve before acceptance. Review is multi-round: REQUEST CHANGES
    findings create bounded fix tasks, forge fixes them, prism verifies the fix,
    and sentinel re-reviews. Repeat until sentinel approves, returns NEEDS
    DISCUSSION, or the review round limit is reached.

[ ] Gate 8: Acceptance (prism) — mandatory for standard/deep/autonomous.
    Prism MUST accept before completion.

EXECUTION RULE: Execute gates in order (1→2→3→4→5→6→7→8), skipping only
unchecked gates. You MAY NOT skip a checked gate. You MAY NOT reorder gates.
Gate 2a runs after research when both are checked, otherwise immediately before
Plan.
```

## Generated Markdown Document Review

Every workflow-generated Markdown document that controls downstream work (`plan-brief.md`, `phase-context.md`, `DESIGN.md`, `ui-research.md`, intake decisions, review summaries) MUST run a self-review loop before the next gate consumes it:

1. Check requirement coverage, exact file paths, runnable commands, evidence/source links, contradictions, and placeholders.
2. If any issue is found, revise the document and run the self-review loop again.
3. Only documents with `Self Review Result: PASS` may unblock planning, implementation, review, or acceptance.

## Context Envelope Template

Every agent prompt MUST be self-contained. Omitting fields = incomplete dispatch. If a field does not apply, write `N/A - <reason>`.

```markdown
## Envelope
- **Goal:** <one-line project goal>
- **Your Task:** <exact task subject from TaskGet>
- **Working Directory:** `<absolute or project-relative cwd>`
- **Completed Dependencies:** <specific outputs now present in git/filesystem>
- **File Scope:** <exact files to create/modify>
- **Test Command:** `<exact command to run for verification>`
- **Acceptance Criteria:** <from task description>
- **Relevant Excerpts:** <requirements/design/code snippets needed to act without reading a separate plan>
- **Intake Decisions:** <adopt/adapt/reject/defer table when external sources were referenced>
- **Constraints:** <project conventions, banned patterns, dependency limits>
- **Out of Scope:** <nearby work the agent must not touch>

## FILES_MODIFIED (required on completion)
List ALL files you created or modified: <path1>, <path2>, ...
```

For implementation agents, append:

```markdown
## Completion Schema
- Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
- Files modified: <same list as FILES_MODIFIED>
- Verification: `<command>` -> <pass/fail + key output>
- RED/GREEN evidence: <required for behavior changes>
- Concerns: <specific risks, or "none">
```

## Agent Dispatch Call

```
Agent({
  name: "<stable-agent-name>",
  description: "<task_subject>",
  subagent_type: "claude-code-flow:<agent>",
  model: "<agent_model>",
  prompt: "<full context envelope + task details>",
  team_name: "<team-name for long tasks, else omit>",
  isolation: "<worktree if conflict detected, else omit>",
  run_in_background: true
})
```

**Dispatch all non-conflicting agents in a single message** (multiple Agent calls). Stable names are required for long tasks so the orchestrator can use `SendMessage` to correct, resume, or shut down idle teammates.

## Parallel Limits

| Agent Type | Max Parallel | Isolation |
|---|---|---|
| forge (code) | 3 | worktree if file conflict |
| prism (tests) | 2 | worktree if file conflict |
| prism (build) | 1 | never parallel |

## File Conflict Analysis

Before dispatching multiple agents simultaneously:
1. Use `TaskGet` on each candidate task to read its description
2. Extract file paths mentioned in "Files:" section or description text
3. If two tasks share any file path → **conflict detected**
4. Conflicting tasks: dispatch with `isolation: "worktree"` (each gets its own branch)
5. Non-conflicting tasks: dispatch without isolation (share worktree)
6. Prefer one agent per file cluster unless the tasks are clearly disjoint.

## Completion Handling

When an agent completes:
1. Read its output — verify status is `DONE` or `DONE_WITH_CONCERNS`
2. Check `FILES_MODIFIED` declaration against task scope
3. Check verification evidence includes command, status, and key output
4. If behavior changed, confirm RED/GREEN evidence or dispatch correction
5. If worktree was used: review changes, merge if clean
6. `TaskUpdate` status=completed only after scope and evidence checks pass
7. Record evidence in `verification-evidence.jsonl`
8. Check if new tasks are now unblocked → dispatch next batch

After every 3 tasks: write key decisions to `<output_dir>/phase-context.md`.

## Error Recovery

```
syntax error     → auto-correct, retry
dependency error → install, retry
logic error      → investigate, fix or escalate
environment error → escalate to user
unknown          → investigate (max 2 retries), escalate
```

## Subagent-Driven Review (deep/autonomous mode)

Use `references/review.md` for review command boundaries, sentinel dispatch inputs, output contract, and fix-loop outcome handling. This section owns only pipeline review scheduling.

For deep and autonomous modes, dispatch each review stage as a **separate sentinel subagent** for zero context contamination:

1. Dispatch sentinel with `review_focus: spec_compliance` in the context envelope → spec-only review.
2. If REQUEST CHANGES: run the multi-round fix loop for spec findings, then re-dispatch a fresh spec sentinel (max 3 rounds).
3. If APPROVE: dispatch a **fresh** sentinel with `review_focus: code_quality` → quality-only review.
4. If REQUEST CHANGES: run the multi-round fix loop for quality findings, then re-dispatch a fresh quality sentinel (max 3 rounds).
5. Only after both stages APPROVE may the pipeline enter acceptance.

For quick/standard: single sentinel run with both stages (no `review_focus` parameter), but REQUEST CHANGES still triggers the same multi-round fix loop.
