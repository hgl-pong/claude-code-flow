---
name: Brainstorming
version: "3.0.0"
description: "Use for ambiguous or substantial product/design decisions before code: new features, major behavior changes, UI/architecture choices, broad refactors, idea exploration, solution generation, assumption testing, or PRD/spec writing. Skip for narrow fixes, approved requirements, routine maintenance, direct execution, or tasks already routed by a command."
argument-hint: "<idea, feature, or problem to explore>"
---

# Brainstorming

Turn ideas into clear designs. The goal is not ceremony — it is to surface assumptions before code makes them expensive.

## Hard Gate

Do not implement until there is an approved design. For tiny work, the design can be two or three sentences. For larger work, write it as a spec.

## Trigger Boundary

Use this skill when there are real decisions to make before implementation:

- The problem, user outcome, or solution is ambiguous.
- The task introduces a new feature or substantial behavior change.
- The work changes UI, architecture, workflow shape, or a broad refactor direction.
- The user explicitly asks to brainstorm, explore, generate options, stress-test an idea, write a PRD, or write a spec.

Skip this skill when the path is already clear:

- The user asks for direct implementation of approved requirements, an approved plan, or a saved spec.
- The task is a narrow bug fix, typo, docs-only edit, test-only edit, config tweak, dependency bump, or routine maintenance.
- A slash command or hook has already routed the task to `/plan`, `/write-plan`, `/execute-plan`, `/quick-fix`, or `dev-orchestrator`; let that route decide whether brainstorming is needed.

## Brainstorming Modes

| Mode | Trigger | Reference |
|------|---------|-----------|
| **Problem Exploration** | "we have a problem", "what should we solve", undefined problem space | This file |
| **Solution Ideation** | "generate solutions", "how to solve", well-defined problem | This file |
| **Assumption Testing** | "stress test this idea", "is this assumption valid", devil's advocate | This file |
| **Strategy Exploration** | "direction", "positioning", "big bets", competitive dynamics | This file |
| **Spec Writing** | "write a spec", "PRD", "requirements doc", "feature specification" | `references/write-spec.md` |

Different situations call for different modes. Identify which fits and adapt. Shift between modes as the conversation evolves.

### Problem Exploration

Use when the user has a problem area but has not defined what to solve.

- Ask "who has this problem?" and "what are they doing about it today?" before anything else
- Map the problem ecosystem: who is involved, what triggers it, what are the consequences
- Distinguish symptoms from root causes — keep asking "why" until you hit something structural
- Surface adjacent problems the user might not have considered
- Ask how the problem varies across user segments

Key questions: "What happens if we do nothing?", "Who has solved a version of this in a different context?", "Is this a problem of awareness, ability, or motivation?"

### Solution Ideation

Use when the problem is well-defined and the user needs multiple possible solutions.

- Generate at least 5-7 distinct approaches before evaluating any
- Vary along dimensions: scope (small tweak vs big bet), approach (product vs process), timing (quick win vs long-term)
- Include at least one "what if we did the opposite?" option
- Include at least one option that removes something rather than adding
- Resist converging too early — if the user latches onto the first idea, push for alternatives

Techniques:
- **Constraint removal**: "What if we had no technical constraints? No budget constraints?" Then work backward.
- **Analogies**: "How does [another industry] solve this?"
- **Inversion**: "How would we make this problem worse? Now reverse each."
- **Decomposition**: Break into subproblems, solve each independently, then combine.

### Assumption Testing

Use when the user has an idea or direction that needs stress-testing.

- List every assumption — stated and unstated
- For each: "How confident are we? What evidence? What would disprove this?"
- Identify the riskiest assumption — the one that kills the idea if wrong
- Suggest the cheapest way to test the riskiest assumption before building
- Play devil's advocate: argue the strongest case against the idea

Categories to probe: user assumptions, problem assumptions, solution assumptions, business assumptions, feasibility assumptions, adoption assumptions.

### Strategy Exploration

Use when the user is thinking about direction, positioning, or big bets.

- Map the playing field: what are the possible strategic moves
- Think in bets: what are we betting on, what are the odds, what is the payoff
- Consider second-order effects: "If we do X, what does that enable or foreclose?"
- Bring in competitive dynamics: "If we do this, how do competitors respond?"
- Think in timeframes: 3 months vs 12 months vs 3 years

## Frameworks (use as thinking tools, not checklists)

### How Might We (HMW)
Reframe problems as opportunities: "How might we [outcome] for [user] without [constraint]?"
- Too broad: "improve onboarding". Too narrow: "add tooltip to step 3".
- Right: "help new users reach first success within 10 minutes"
- Generate 5-10 HMW questions from a single problem statement

### Jobs-to-be-Done (JTBD)
Think from the user's job: "When [situation], I want to [motivation] so I can [outcome]."
- The job is stable even when solutions change
- Ask "What did they fire to hire your product?" — reveals real competitive set

### Opportunity Solution Trees
```
Desired Outcome
├── Opportunity A (user need)
│   ├── Solution A1 → Experiment: ...
│   └── Solution A2 → Experiment: ...
├── Opportunity B
│   └── Solution B1 → Experiment: ...
```
Opportunities come from research. Multiple solutions per opportunity. Multiple experiments per solution.

### First Principles
1. State the problem or assumption
2. Break into fundamental components
3. Question each: "Why does this have to be this way? Law of physics or convention?"
4. Rebuild from ground up

Use when: stuck in incremental thinking, "that's just how it works" thinking.

### SCAMPER
7 lenses on an existing product. Apply each to break out of incremental thinking:
- **Substitute**: What component/material/process could be replaced?
- **Combine**: What two features/ideas could merge into something stronger?
- **Adapt**: What works elsewhere that could be adapted here?
- **Modify**: What could be magnified, minimized, or reshaped?
- **Put to other use**: Could this serve a different audience or context?
- **Eliminate**: What feature/step could be removed entirely?
- **Reverse**: What happens if you reverse the order, role, or sequence?

### OODA Loop (Observe-Orient-Decide-Act)
Favor tempo over perfection. Observe signals, orient through mental models, decide as hypothesis, act to test. Cycle faster than competition. Most teams get stuck in Orient — OODA forces action.

### Reverse Brainstorming
1. Invert: "How could we make onboarding as confusing as possible?"
2. Generate "make it worse" ideas
3. Reverse each into a solution
4. Evaluate reversed ideas

## Session Structure

The facilitation framework. Each phase maps to the implementation Process below: Frame → (1) Explore context + (2) Clarify; Diverge → (3) Compare approaches; Provoke → (3) Compare approaches (stress-test); Converge → (4) Present design; Capture → (5) Save spec.

1. **Frame** — What are we exploring? Why now? What do we know? Constraints? Great outcome?
2. **Diverge** — Many ideas, no judgment. Push past the first 3-5 obvious ones.
3. **Provoke** — Challenge thinking: "Strongest argument against?", "Who would hate this?", "What if the opposite were true?"
4. **Converge** — Group themes, evaluate against impact/feasibility/alignment, identify top 2-3, name biggest unknown for each.
5. **Capture** — Key ideas, assumptions to test, next steps, what was explicitly set aside.

## Process

1. **Explore context** — Read relevant docs, commands, skills, agents, nearby code. Note existing patterns.
2. **Clarify** — Ask one focused question at a time. Prefer multiple-choice for trade-offs.
3. **Compare approaches** — Present 2-3 viable approaches with trade-offs, risks, recommendation.
4. **Present the design** — Scope, files/modules, data flow, error handling, tests, rollout. Scale detail to risk.
5. **Save the spec** — `.claude/flow/designs/<topic>-design.md` (goals, non-goals, approach, tasks, risks, verification). This is a design SPEC, not DESIGN.md (the visual design system). DESIGN.md goes to project root.

## Spec Self-Review

Before user review:
- Placeholder scan — no TBD/TODO/vague sections
- Internal consistency — sections don't contradict
- Scope check — focused enough or needs decomposition
- Ambiguity check — any requirement interpretable two ways?
- No bundled refactors
- Testable requirements
- Risks have verification steps

## Anti-Patterns

- **Solutioning before framing** — "We should build X" before defining the problem
- **Feature parity trap** — "Competitor has X so we need X" — ask what user need X serves
- **Anchoring on constraints** — Set constraints aside in divergent mode
- **One-idea brainstorm** — Acknowledge first idea, then push for alternatives
- **Analysis paralysis** — If circling, prompt: "If you had to pick one direction right now?"

## If Connectors Available

If **~~code-intel** is connected:
- Query existing patterns to ground brainstorming in codebase reality
- Check impact of proposed approaches on existing symbols

## Tips

1. **Be opinionated** — "I think approach B is stronger because..." beats listing pros/cons
2. **Match the stage** — Early exploration gets different feedback than final polish
3. **Name the pattern** — If you recognize a common trap (solutioning too early, scope creep), name it directly

## Handoff

After approval, invoke **SUGGESTED: `writing-plans`** for multi-step work or the lightweight TDD path for narrow changes. Do not invoke `using-claude-code-flow` again after this handoff; the route is already selected.
