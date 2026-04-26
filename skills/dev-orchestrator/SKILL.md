---
name: Dev Orchestrator
version: "2.0.0"
description: This skill should be used when the user asks to "develop a feature", "implement a system", "design architecture", "build an API", "refactor a module", or any multi-step development task that benefits from agent orchestration and model-tiered delegation. Triggers on complex development tasks where planning, implementation, testing, and review should be coordinated.
---

# Development Orchestrator

Orchestrate tasks through Plan -> Implement -> Review pipeline with model-tiered agents, mode selection, DAG-aware scheduling, and dynamic error recovery.

## Common Rationalizations — Reality Check

When you feel tempted to skip a step, check this table first:

| Rationalization | Reality |
|---|---|
| "This is simple enough to skip planning" | Simple tasks have hidden complexity. The 2-minute plan saves 20-minute rework. |
| "I can just implement this directly" | Direct implementation without review misses edge cases. Use the pipeline. |
| "The review will slow us down" | Review catches 40%+ of bugs before they compound. Skipping it is false speed. |
| "This subagent can figure out the context" | Subagents build no context from nothing. Construct their prompt precisely. |
| "The user won't want to approve this" | Gates exist because agents miss things humans catch. Present the gate. |
| "I already know what they need" | What you know and what the user needs are not always the same. Ask, don't assume. |

## Agent Roster

| Agent | Model | Role | Gate |
|-------|-------|------|------|
| `scout` | sonnet | Web research, docs lookup, tech comparison | Research |
| `oracle` | opus | Implementation planning, HTML visualization | Plan |
| `atlas` | opus | Architecture design, module decomposition | Design |
| `designer` | sonnet | UI/UX interaction design documents | UI Design |
| `forge` | sonnet | Code implementation (backend, general) | -- |
| `weaver` | sonnet | Frontend implementation (React/Vue/Svelte) | -- |
| `prism` | sonnet | Test frameworks, benchmarks | -- |
| `anvil` | haiku | Build, CI/CD, dependencies | -- |
| `sentinel` | sonnet | Code review before commit | Review |
| `chronicler` | sonnet | Documentation, changelogs, API docs | -- |

## Mode Selection — Smallest Mode That Fits

After analysis, select the appropriate workflow mode:

| Mode | When | Research | Design | Plan Approval | Review | Auto-retry |
|------|------|----------|--------|---------------|--------|------------|
| **quick** | Bug fix, single file, config change | No | No | No | Optional | No |
| **standard** | Feature addition, multi-file change | If needed | No | Yes | Yes | No |
| **deep** | New system, architecture refactor, complex integration | Yes | Yes | Yes (HTML) | Yes | Yes |
| **autonomous** | User gives goal, expects full delivery | Auto | Auto | Auto | Auto (max 3) | Yes |

Set mode via:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>
```

Auto-recommend logic:
- 1-2 subtasks, single domain, no external deps → **quick**
- 3-5 subtasks, known codebase → **standard**
- 6+ subtasks, new system, cross-module → **deep**
- User says "figure it out" / "just ship it" → **autonomous**

User can override the recommendation. If user specified `--mode` in `/workflow-plan`, use that mode.

## Pipeline

```
Mode Selection
      |
      v
Research (scout) -- if needed (skipped in quick mode)
      |
      v
Plan Gate (oracle)
  quick:   skip or minimal inline plan
  standard: text summary -> inline approval
  deep:    HTML viz -> browser review
  auto:    auto-approve
      |
      v
Design Gate (atlas) -- only for deep mode / new systems
      |
      v
UI Research (scout) -- only for frontend-ui tasks, skipped in quick mode
  scout researches similar products, design trends, best practices
  reusable knowledge written to persistent memory (type: reference)
      |
      v
UI Design Gate (designer) -- only for frontend-ui tasks
  designer produces design doc based on research -> user approval -> handoff to weaver
      |
      v
Implementation (forge/weaver + prism + anvil)
  DAG-aware scheduling for deep/standard
  Direct call for quick
  Agent selection based on skill match:
    frontend-ui tasks -> weaver implements
    all other tasks   -> forge implements
      |
      v
Review Gate (sentinel)
  quick:   optional
  standard/deep: mandatory
  auto:    auto-handle feedback (max 3 rounds)
      |
      v
Documentation (chronicler) -- if needed
      |
      v
Report & Done
```

## State Machine

Write state at each transition:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase <phase>
```

Valid transitions:
```
idle -> research     (external info needed)
idle -> plan         (no research needed)
research -> plan     (research complete)
plan -> design       (plan approved, needs architecture)
plan -> impl         (plan approved, no architecture needed)
plan -> ui-research  (plan approved, frontend-ui task, no architecture needed)
design -> impl       (design approved, non-UI task)
design -> ui-research (design approved, frontend-ui task)
ui-research -> ui-design (research complete, ready for design)
ui-design -> impl    (UI design approved)
impl -> review       (implementation complete)
review -> impl       (review failed, back to implementer)
review -> idle       (review passed)
impl -> idle         (simple/quick task, skip review)
* -> idle            (user cancels or error)
```

## Context Preservation

| File | Written by | Read by | Content |
|------|-----------|---------|---------|
| `.claude/flow/workflow-state.json` | flow-state.py | statusline, orchestrator | Phase, mode, task progress, retry count |
| `.claude/flow/phase-context.md` | oracle/atlas/designer | forge/weaver/sentinel | Approved plan, architecture decisions, design research summary, UI design document |
| `.claude/flow/ui-research.md` | scout | designer | Design research findings: trends, similar products, best practices |
| `.claude/flow/modified-files.txt` | track-changes.py | sentinel | Files modified (plain list) |
| `.claude/flow/modified-files.jsonl` | track-changes.py | orchestrator | File ownership log (file, action, agent, ts) |
| `.claude/flow/review-result.txt` | sentinel | orchestrator | Latest review outcome |
| `.claude/flow/task-graph.json` | oracle | orchestrator | DAG task structure |

**Phase handoff protocol:**
1. After plan approval: oracle writes plan summary to `phase-context.md` with YAML frontmatter (written_by, phase, timestamp, session_id, task_summary)
2. After design approval: atlas appends architecture decisions to `phase-context.md`
3. After UI research: scout writes research report to `.claude/flow/ui-research.md`, orchestrator appends summary to `phase-context.md` under `## Design Research Summary`, and writes reusable knowledge to persistent memory
4. After UI design approval: designer appends design document to `phase-context.md` under `## UI Design Document`
5. Before review: orchestrator lists modified files for sentinel
6. After review: sentinel writes outcome to `review-result.txt`

## Step 1: Analyze + Mode Select

Classify the task:
- **Domain**: What area of the codebase is affected
- **Complexity**: Simple (1-2 subtasks) vs Complex (3+ subtasks, cross-cutting)
- **Needs design**: Yes (new system) vs No (bug fix, feature addition)
- **Needs research**: Yes (external library/API) vs No (internal-only)

Select mode based on the classification (see Mode Selection table above).
Set mode and initial phase:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-mode <mode>
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
```

## Step 2: Research (if needed)

Skip for: quick mode, internal-only tasks, or when user already has context.

Invoke scout when external information is needed (library docs, API references, tech comparisons).

```
Agent({
  name: "researcher",
  subagent_type: "claude-code-flow:scout",
  model: "sonnet",
  prompt: """
  Research topic: [specific question or area]
  Context: [task description]
  What we need: [specific information gaps]
  """
})
```

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase plan
```

## Step 3: Plan Gate

**quick mode**: Skip to implementation. At most, write a 2-line plan inline.

**standard mode**: Invoke oracle for text summary (files to change, risks, approach).

**deep mode**: Invoke oracle for HTML visualization (architecture, phases, dependencies, risk table).

**autonomous mode**: Invoke oracle. Auto-approve the plan.

After approval, oracle writes plan summary to `.claude/flow/phase-context.md` with frontmatter.

For standard/deep/autonomous modes, oracle also generates `.claude/flow/task-graph.json` (see Step 5: DAG Scheduling).

## Step 4: Design Gate (if needed)

Skip for: quick/standard mode, bug fixes, small features.

For new systems or architectural changes (deep/autonomous mode):
1. Spawn **atlas** (Opus) with approved plan as context
2. atlas produces: module design, API surface, data layout, file structure
3. Present to user for confirmation (auto-approve in autonomous mode)
4. After approval, atlas appends to `phase-context.md`

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase design
```

## Step 4a: UI Research (for frontend-ui tasks only)

Skip for: quick mode, non-UI tasks.

Detection: After Plan Gate (or Design Gate), if skill-detector matched `frontend-ui`, route to UI Research before UI Design Gate.

Process:
1. Spawn **scout** (Sonnet) with a targeted design research prompt
2. Scout researches:
   - Similar product UI patterns (2-3 comparable products)
   - Cutting-edge design trends for the specific component/page type
   - Best practices and common anti-patterns
   - Notable open-source implementations or design systems
3. Scout produces a structured research report with a "Reusable Design Knowledge" section
4. Orchestrator extracts reusable knowledge and writes to persistent memory (type: reference, file: `design-reference-<topic-slug>.md`)
5. Research report is saved to `.claude/flow/ui-research.md`
6. A 3-5 bullet summary is appended to `phase-context.md` under `## Design Research Summary`

**Memory writing criteria** — write to persistent memory when a finding meets ALL:
- Reusable: applies to multiple projects, not just current task
- Durable: relevant for 6+ months
- Concrete: specific enough to be actionable
- Verified: found in 2+ credible sources

```
Agent({
  name: "ui-researcher",
  subagent_type: "claude-code-flow:scout",
  model: "sonnet",
  prompt: """
  Research topic: Design research for [component/page type]

  Context: [task description from approved plan]

  Research scope:
  1. Find 2-3 similar products or well-known implementations of [component/page type].
     Focus on: layout patterns, interaction flows, information architecture, visual hierarchy.

  2. Identify current design trends (2025-2026) relevant to [component/page type].
     Search for: recent design system updates, popular component libraries, award-winning UI examples.

  3. Find best practices and anti-patterns for [component/page type].
     Focus on: accessibility considerations, responsive behavior, performance implications.

  4. Identify notable open-source design systems or component libraries that implement [component/page type].
     Examples: Radix UI, shadcn/ui, Material Design 3, Apple HIG, Ant Design.

  Output format:
  ### Similar Product Analysis
  For each product: Product name/URL, pattern used, strengths, weaknesses, applicability to our task.

  ### Design Trends
  Trend name with description, source URL, and how it applies to our component/page type.

  ### Best Practices
  Practice with explanation and source reference.

  ### Anti-Patterns to Avoid
  Anti-pattern with explanation and what to do instead.

  ### Reusable Design Knowledge
  Findings valuable across multiple projects (not task-specific):
  - Knowledge topic (e.g., "dashboard layout patterns 2026")
  - Brief summary (2-3 sentences)
  - Why this is reusable
  """
})
```

After scout completes:
1. Save full research report to `.claude/flow/ui-research.md`
2. Extract reusable design knowledge from the "Reusable Design Knowledge" section
3. Write reusable knowledge to persistent memory (check for existing `design-reference-*.md` to avoid duplicates)
4. Append summary to `phase-context.md`:
   ```markdown
   ## Design Research Summary
   - [Key finding 1]
   - [Key finding 2]
   - [Key finding 3]
   Full research report: `.claude/flow/ui-research.md`
   ```

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase ui-research
```

After research complete:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase ui-design
```

## Step 4b: UI Design Gate (for frontend-ui tasks only)

Skip for: non-UI tasks, backend-only features, tasks matched to other skills.

Detection: After Plan Gate (or Design Gate), if skill-detector matched `frontend-ui`, route to UI Design Gate.

Process:
1. Spawn **designer** (Sonnet) with approved plan, task description, and research findings as context
2. designer produces structured UI/UX design document covering:
   - Component hierarchy and data flow
   - Interaction flows and state transitions
   - Responsive breakpoints and layout behavior
   - Accessibility requirements (WCAG 2.1 AA)
   - Design tokens (colors, typography, spacing)
   - Design research integration: which patterns/trends from research are adopted and why
3. Present design document to user for confirmation (auto-approve in autonomous mode)
4. After approval, designer's output is appended to `phase-context.md` under `## UI Design Document`
5. DAG task graph is updated: weaver tasks depend on designer task completion

```
Agent({
  name: "ui-designer",
  subagent_type: "claude-code-flow:designer",
  model: "sonnet",
  prompt: """
  Task: [task description]
  Approved plan: .claude/flow/phase-context.md
  Design research: .claude/flow/ui-research.md
  Design constraints: [existing UI framework, component library, styling approach]
  Accessibility level: WCAG 2.1 AA
  Target breakpoints: mobile <640px, tablet 640-1024px, desktop >1024px

  Important: Read the design research report (.claude/flow/ui-research.md) and incorporate
  relevant findings into your design. Reference which patterns or trends you're adopting
  and explain why. You are not required to follow any specific finding — use your judgment.
  """
})
```

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase ui-design
```

## Step 5: Implementation (DAG-Aware Scheduling)

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase impl
```

### DAG Task Graph

For standard/deep/autonomous modes, tasks are structured as a DAG in `.claude/flow/task-graph.json`:
```json
{
  "nodes": [
    {"id": "T1", "title": "...", "agent": "forge", "status": "pending", "dependencies": [], "files": [...]},
    {"id": "T2", "title": "...", "agent": "forge", "status": "pending", "dependencies": ["T1"], "files": [...]}
  ],
  "edges": [["T1","T2"]]
}
```

For frontend-ui tasks, the DAG includes scout research, designer, and weaver:
```json
{
  "nodes": [
    {"id": "T1", "title": "Research login page design patterns", "agent": "scout", "status": "pending", "dependencies": [], "files": []},
    {"id": "T2", "title": "Design login page UI", "agent": "designer", "status": "pending", "dependencies": ["T1"], "files": []},
    {"id": "T3", "title": "Implement login page", "agent": "weaver", "status": "pending", "dependencies": ["T2"], "files": [...]},
    {"id": "T4", "title": "Write login page tests", "agent": "prism", "status": "pending", "dependencies": ["T3"], "files": [...]}
  ],
  "edges": [["T1","T2"],["T2","T3"],["T3","T4"]]
}
```

### Scheduling Loop

```
while get-ready tasks exist:
  1. Run: python hooks/scripts/task-graph.py get-ready
  2. Group ready tasks by agent type
  3. Spawn agents in parallel for independent tasks (max 2 parallel agents)
  4. On completion: set-status <id> done, update task progress
  5. Check for failed tasks -> dynamic re-planning (Step 7)
  6. Loop back to 1
```

**Parallel rules:**
- forge + prism can parallel if tests are for existing code
- anvil can parallel with prism
- Tasks with shared file dependencies must NOT run in parallel
- Use `modified-files.jsonl` ownership data to detect potential conflicts

**Agent routing for UI tasks:**
- Tasks with `agent: "scout"` run first and produce design research (can parallel with backend forge tasks)
- Tasks with `agent: "designer"` depend on scout research and produce the design document
- Tasks with `agent: "weaver"` depend on designer tasks and implement the frontend
- Tasks with `agent: "forge"` may still appear in the same DAG for non-UI subtasks (e.g., backend API endpoints needed by the frontend)
- scout and designer must NOT run in parallel (designer depends on scout research)
- designer and weaver must NOT run in parallel (weaver depends on designer output)
- scout and forge CAN run in parallel (design research + backend work are independent)
- forge and weaver CAN run in parallel if they work on different files (e.g., backend API + frontend UI)

**quick mode**: Skip DAG. Direct single forge call.

Update task progress:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-tasks <done> <total>
```

### Context Management

- After every 3 completed tasks, generate an intermediate state summary
- Write key decisions to `phase-context.md` incrementally
- If remaining tasks > 5, suggest the user allow context compaction
- On compaction, `on-compact.py` preserves current state to `pre-compact-context.md`

## Step 6: Review Gate

Write state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase review
```

**quick mode**: Review is optional. Ask user if they want it.

**standard/deep mode**: Always invoke sentinel.

**autonomous mode**: Auto-invoke sentinel and auto-handle feedback.

```
Agent({
  name: "reviewer",
  subagent_type: "claude-code-flow:sentinel",
  model: "sonnet",
  prompt: """
  Task: [task description]
  Plan reference: .claude/flow/phase-context.md
  Files created: [list from modified-files.jsonl]
  Focus areas: [specific concerns]
  """
})
```

Outcomes:
- APPROVE -> write to `review-result.txt`, proceed
- REQUEST CHANGES -> back to forge with specific feedback -> re-review
- NEEDS DISCUSSION -> present to user

Max 3 review rounds. Escalate to user after that.

For frontend-ui tasks, sentinel should also check:
- Accessibility (ARIA attributes, keyboard navigation, screen reader support)
- Responsive design (layout at specified breakpoints)
- Design document adherence (component matches design spec)
- Performance (bundle size, render performance, unnecessary re-renders)

### Rule Check

If `.claude/flow/rules.json` exists, sentinel also checks modified files against accumulated rules. Any violations are flagged as "RULE VIOLATION" in the review report.

## Step 7: Dynamic Re-Planning (Error Recovery)

When a task fails, use the four-level decision framework:

```
Failure detected
  -> Classify error: syntax / dependency / logic / environment / unknown
  |
  +-- syntax error     -> FIX: auto-correct and retry
  +-- dependency error -> FIX: install missing dependency and retry
  +-- logic error      -> INVESTIGATE: analyze context, then FIX or ESCALATE
  +-- environment error -> ESCALATE: needs user intervention
  +-- unrelated issue   -> NOTE: record as known issue, skip and continue
  +-- unknown           -> INVESTIGATE -> max 2 FIX attempts -> ESCALATE
```

Implementation:
1. On agent failure, log error: `python hooks/scripts/flow-state.py set-error <task_id> <type> <message>`
2. Increment retry: `python hooks/scripts/flow-state.py inc-retry`
3. Based on error classification:
   - **FIX**: Re-invoke agent with error context. Prompt: "Previous attempt failed with: [error]. Fix the issue and retry."
   - **INVESTIGATE**: Read relevant files, check error logs, analyze context. Then decide FIX or ESCALATE.
   - **NOTE**: Write to `phase-context.md` as a known caveat. Mark task as done with a note. Continue with remaining tasks.
   - **ESCALATE**: Pause workflow. Present to user with options: retry manually, skip step, or cancel.
4. Record the decision and resolution to `.claude/flow/error-log.jsonl`

Max retries per task: 2. After that, always ESCALATE.

## Step 8: Documentation (optional)

After implementation passes review, invoke chronicler if:
- The feature adds new public APIs
- The user requested documentation
- The project has a docs/ directory with existing documentation

## Step 9: Report & Done

Write final state:
```bash
python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/flow-state.py set-phase idle
```

Present final summary:
- What was implemented
- Files created/modified (from modified-files.jsonl ownership data)
- Test results
- Review outcome
- Any known issues noted during execution

## Prompting Guidelines

For all agents, include: Context, Scope, Constraints, Dependencies, Output.

### Subagent Prompt Construction

Subagents get fresh context — they never inherit your session history. This means YOU are responsible for giving them everything they need:

1. **NEVER let a subagent read the plan file themselves.** Paste the relevant sections directly into their prompt. Agents given a file path will produce vaguer results than agents given the actual content.
2. **Construct exactly what they need — no more, no less.** Too much context dilutes focus; too little causes NEEDS_CONTEXT escalations.
3. **Include a "Questions?" gate:** Tell the subagent to ask questions BEFORE starting work. This catches scope misunderstandings early.
4. **Specify the output format:** Tell the subagent exactly what you expect back (status code + specific deliverables).

For **scout**: research topic, info gaps, how findings feed into planning.
For **scout (design research)**: component/page type to research, similar products to compare, design trends scope, what reusable knowledge to extract.
For **oracle**: complexity level, mode, HTML requirement, research findings.
For **atlas**: approved plan, system boundaries, constraints, integration points.
For **designer**: task requirements, existing UI framework, design constraints, accessibility level, target breakpoints, design research findings from `.claude/flow/ui-research.md`.
For **forge**: specific files, plan reference, task from DAG, related files to avoid breaking.
For **weaver**: design document path (phase-context.md), specific components to implement, existing project frontend patterns, styling approach.
For **sentinel**: files to review, plan path, focus areas, rules to check.
For **chronicler**: doc style, target audience.

## Verification Before Completion

```
IRON LAW: NEVER claim a phase is complete without fresh verification evidence.
Claiming work is complete without verification is dishonesty, not efficiency.
```

Before reporting any phase as complete:

1. **Run verification** — build, tests, lint. Don't trust, verify.
2. **Read the actual output** — don't assume the agent did what you asked.
3. **Verify against acceptance criteria** — check every criterion from the plan.
4. **Only then** mark the task complete.

| Claim | Required Evidence | Insufficient |
|-------|------------------|--------------|
| "Tests pass" | Actual test output showing pass/fail counts | "I wrote the tests" |
| "Build succeeds" | Actual build command output | "The code should compile" |
| "Implementation matches plan" | Line-by-line comparison of requirements vs code | "I followed the plan" |
| "Review passed" | Sentinel report with APPROVE | No critical issues found (by you) |

## Review Gate — Two-Stage Review

The review gate uses two distinct stages. NEVER run Stage 2 before Stage 1 passes.

**Stage 1: Spec Compliance** — "Did they build the right thing?"
- Read the approved plan from `phase-context.md`
- Read every modified file
- For each requirement, verify it exists in the implementation
- Check for missing requirements, extra work, misunderstandings
- If Stage 1 fails → REQUEST CHANGES → back to implementation

**Stage 2: Code Quality** — "Did they build it right?" (only after Stage 1 passes)
- Correctness, security, performance, architecture
- Sentinel's full review checklist
- Rule violations from `rules.json` if it exists
