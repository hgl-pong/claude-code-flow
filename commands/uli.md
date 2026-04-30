---
name: uli
description: "Ultra Loop Iteration — autonomous product iteration. Type 'uli' in prompt or /uli <goal>. PD agent proposes requirements each cycle, dev pipeline executes, hard acceptance validates. Loops until goal reached or max_iterations."
---

# ULI — Ultra Loop Iteration Mode

**Tell it what to build. It iterates until it's done.**

## Activation

```
uli build a CLI tool that generates project scaffolding
uli add authentication to this app
/uli this product needs a working test suite and CI pipeline
```

Everything after "uli" becomes the product goal.

## How It Works

```
User prompt → uli-detector hook → ULI MODE ACTIVE → ultrawork skill (ULI branch)
→ Write state + product-state.md
→ ┌── Iteration Loop (max 10) ──┐
│   PD: propose requirements     │
│   Dev Pipeline: TDD impl       │
│   Hard Acceptance: build+test+features │
│   ACCEPT → next iteration      │
│   REJECT → retry max 2x → escalate │
→ └───────────────────────────────┘
→ <uli-done>
```

## ULI vs ULW

| | ULW | ULI |
|---|---|---|
| Scope | One task | Product goal, N iterations |
| PD agent | No | Yes — proposes each iteration |
| Acceptance | Soft (tests + build) | Hard (build + tests + features) |
| Loop | `<ulw-done>` when done | `<uli-done>` when goal reached |

## Use When

- Autonomous product development over multiple iterations
- Product goal but no specific task breakdowns
- Want system to decide what to build next

## Do Not Use When

- One specific task → `/ulw`
- Want to approve plan first → `/workflow-plan`
- Ambiguous, want exploration → `/brainstorm`

## Process

See ULI branch in `ultrawork` skill for full execution logic.
