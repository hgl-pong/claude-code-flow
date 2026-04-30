---
name: uli
description: Ultra Loop Iteration — fully autonomous product iteration mode. Type "uli" anywhere in your prompt, or use /uli <product goal>. A PD agent proposes requirements each iteration, the dev pipeline executes them, hard acceptance validates delivery, and the loop continues until the product goal is reached or max_iterations. No human gates. No confirmation prompts.
---

# ULI — Ultra Loop Iteration Mode

**Tell it what to build. It iterates until it's done.**

ULI is the product iteration mode of claude-code-flow. Mention `uli` anywhere in your message to activate it. A PD (Product Manager) agent analyzes the current state of the product and proposes what to build next — then the full dev pipeline executes it, acceptance validates it, and the loop repeats.

## Activation

Any of these work:

```
uli build a CLI tool that generates project scaffolding
uli add authentication to this app
/uli this product needs a working test suite and CI pipeline
```

Everything after "uli" becomes the product goal.

## How It Works

```
User prompt (with "uli")
    ↓
uli-detector hook fires → ULI MODE ACTIVE injected
    ↓
Invoke ultrawork skill (ULI branch)
    ↓
Write uli-state.json + product-state.md
    ↓
┌──────────── Iteration Loop (max 10) ────────────┐
│                                                  │
│  PD agent                                        │
│  ├─ reads: product-state.md + last acceptance    │
│  └─ writes: uli-proposal.md (CORE requirements)  │
│                                                  │
│  Dev Pipeline                                    │
│  ├─ oracle: decompose requirements into tasks    │
│  ├─ forge/weaver + prism: TDD implementation     │
│  └─ sentinel: code review (auto, max 2 loops)    │
│                                                  │
│  Hard Acceptance Gate                            │
│  ├─ build PASS + tests PASS + features PASS      │
│  ├─ ACCEPT → update product-state.md → next iter │
│  └─ REJECT → retry max 2x → escalate to user    │
│                                                  │
└──────────────────────────────────────────────────┘
    ↓
<uli-done> with full iteration summary
```

## What Makes ULI Different from ULW

| | ULW (Ultrawork) | ULI (Ultra Loop Iteration) |
|---|---|---|
| **Scope** | One task, one delivery | Product goal, N iterations |
| **Intent classification** | Yes (implement/fix/refactor/etc.) | No — always "build product" |
| **PD agent** | No | Yes — proposes requirements each iteration |
| **Acceptance** | Soft (tests + build) | Hard (build + tests + feature checklist) |
| **Retry on failure** | 2 loops then escalate | 2 loops per iteration then escalate |
| **Loop termination** | `<ulw-done>` when task complete | `<uli-done>` when goal reached or max iterations |
| **Completion signal** | `<ulw-done>` | `<uli-done>` |
| **max iterations** | 25 (re-injection loops) | 10 (full dev cycles) |

## What Gets Skipped

| Gate | Normal Mode | ULI |
|---|---|---|
| Brainstorm approval | User confirms | PD agent decides |
| Plan approval (oracle) | User confirms | Auto-approved |
| Architecture approval (atlas) | User confirms | Auto (deep tasks only) |
| UI design approval (designer) | User confirms | Auto-approved |
| Review round (sentinel) | User sees result | Auto-handled (max 2 loops) |
| Acceptance (validator) | User sees result | Hard gate — REJECT blocks next iteration |

## What Is Never Skipped

- **PD agent** — runs every iteration to propose requirements
- **testing-strategy** — write the failing test first, every time
- **Hard acceptance** — build + tests + feature checklist must ALL pass
- **product-state.md update** — records completed features for PD's next iteration
- **Error escalation** — after 2 retries, stop and report to user

## State Files

| File | Purpose |
|---|---|
| `.claude/flow/uli-state.json` | Current iteration, phase, acceptance status |
| `.claude/flow/product-state.md` | Product goal + completed features (updated each ACCEPT) |
| `.claude/flow/uli-proposal.md` | Current iteration's requirements from PD |
| `.claude/flow/uli-acceptance-report.md` | Last iteration's acceptance verdict + gap list |

## Use When

- You want autonomous product development over multiple iterations
- You have a product goal but not specific task breakdowns
- You want the system to decide what to build next based on current state
- You want hard acceptance enforced between each iteration

## Do Not Use When

- You have one specific task → use `/ulw <task>`
- You want to discuss or approve the plan before implementation → use `/workflow-plan`
- The task is ambiguous and you want option exploration → use `/brainstorm`
- You need real-time control over what gets built → use standard mode

## Process

See the ULI branch in the `ultrawork` skill for the full execution logic.
