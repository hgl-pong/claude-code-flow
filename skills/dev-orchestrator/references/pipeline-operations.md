# Pipeline Operations Reference

Detailed gate specifications and scheduling rules for the development pipeline. This reference is the harness control-plane contract for explicit gates, durable state, hook-enforced policy, and evidence-based completion; dispatch mechanics live in `parallel-dispatch.md`.

## Policy Trace

Each gate decision must leave a short trace in the active plan or phase context: checked/skipped, reason, owner, and required evidence. Hooks may enforce deterministic policy (routing, dangerous tools, completion blocking), but product judgment stays in the orchestrator/oracle path.

## Mandatory Gate Checklist (Full)

```
GATE CHECKLIST (evaluate for this specific task):

[ ] Gate 0: Requirement Clarification — mandatory before classification when any
    request is vague or underspecified: missing concrete scope, constraints,
    success criteria, acceptance criteria, target files/areas, or expected behavior.
    Do not answer "I'll do the minimal version" for vague outcome requests. Minimum
    implementation is allowed only inside an approved, decomposed task slice; it is
    not an entry response for broad work. Ask what to build/change, what files/areas
    or pages/sections are involved, target users when relevant, style references when
    relevant, constraints, and acceptance criteria; then proceed through the normal
    gates. Product/UI/site/design-system outcomes require extra care: if scope,
    pages, audience, visual direction, content, or success criteria are unclear,
    clarify before classification.

[ ] Gate 1: Brainstorm — mandatory for: new features, behavior changes, UI work,
    architecture changes, broad refactors. Skip only for: narrow bug fixes with
    known root cause, config changes, single-file edits with clear spec.

[ ] Gate 2: Research (general-purpose subagent + research skill) — default-on
    before plan. First classify the request by estimated size. Very lightweight
    tasks may skip research/plan: changing only a few lines, touching 1-2 files,
    or adding 1-2 small files with obvious scope. Every task that is not very
    lightweight MUST use the full flow with planning-stage subagents. Heavy triggers
    include: more than 5 touched files, more than 3 newly created files, broad
    behavior/workflow/prompt/hook/test changes, architecture/UI changes, unfamiliar
    code, quality-sensitive outcomes, or outcome-oriented requests without exact
    implementation scope. UI/site work is one example, not the whole rule. When
    unsure, classify as not very lightweight and dispatch planning-stage subagents.
    Research MUST include local file inspection. Include external research only
    when external facts, library/API behavior, competitive/product comparison, or
    current ecosystem knowledge materially affect the solution, unless the user
    forbids network access or the environment cannot access the network. Produce
    a subagent-authored written research artifact before plan when research is required;
    chat-only synthesis is not enough. Strong research is a quality gate:
    it determines whether the final solution is merely functional or competitive.
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
    very lightweight tasks using the size criteria from Gate 2. For every task that is
    not very lightweight, dispatch oracle; main-conversation planning is not enough.
    Oracle/orchestrator MUST produce a plan document at `<output_dir>/plan-brief.md`
    with TaskCreate tasks before any implementation task creation, forge dispatch, or
    direct code edit starts.
    A chat-only proposal, option list, or "confirm and I will start" response is not a
    plan artifact. The plan document MUST include Local Research, External Research,
    Success Criteria, Verification, and Self Review Result sections. Oracle MUST
    receive research findings as input when Gate 2 was checked and intake decisions
    as input when Gate 2a was checked.

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
    when task domain is frontend-UI AND the task is not very lightweight. Research subagent
    MUST produce ui-research.md with CONCRETE data:
    a) Local codebase: existing components, styling approach (Tailwind/CSS Modules/etc),
       actual CSS variables and font imports in use.
    b) Competitor analysis: 2-3 products — hex values, font names, layout structure,
       spacing density, component personality, NOT vague "uses a nice palette".
    c) Design intelligence: specific font pairings, type scale ratios, color families
       for this domain, grid systems, dark mode strategies.
    Research MUST complete before Gate 6 (UI Design) starts.

[ ] Gate 6: UI Design (ui-design skill) — mandatory when task domain is frontend-UI
    AND the task is not very lightweight. UI design skill MUST produce DESIGN.md following the
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

## Dispatch Mechanics Boundary

Use `parallel-dispatch.md` for context envelopes, Agent call shape, file-conflict analysis, parallel limits, team mode, completion handling, handoff protocol, and dispatch error recovery.

This reference only decides which gates are checked and in what order. After Gate 3a approval, pass the approved task graph and gate decisions to `parallel-dispatch.md` for execution scheduling.

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

- Deep/autonomous modes require separate spec-compliance and code-quality sentinel stages before acceptance.
- Quick/standard modes may use one sentinel run when review is checked.
- Any REQUEST CHANGES result stays in Gate 7 until `review.md`'s fix-loop outcome permits acceptance or escalation.

## Continuous Execution Rule

Once a plan, ULI proposal, or approved workflow gate authorizes execution, do not pause to ask whether to continue between tasks. Continue until all unblocked tasks are complete, a checked gate fails, a blocker needs user input, or the user interrupts. Status updates are fine; "should I continue?" checkpoints are not.

Reference intake decisions must remain explicit: every external workflow idea is marked Adopt / Adapt / Reject / Defer, and accepted ideas strengthen existing agents, skills, commands, hooks, rules, docs, or runtime surfaces. Intake must not import a parallel skill catalog, duplicate agent taxonomy, new command system, hook runtime, daemon, installer, or external control plane unless the user approves that as a separate design.

## Workflow State Gate

Every non-lightweight gate transition updates workflow-state.json or the active phase context with phase, mode, owner, status, evidence pointer, and next blocked/unblocked action. Chat summaries do not replace this durable state.

## Ten-Iteration Regression Contract

Workflow orchestration changes must keep regression coverage tied to workflow-state.json and verification-evidence.jsonl so routing, dispatch, review, and acceptance claims remain observable instead of conversational.
