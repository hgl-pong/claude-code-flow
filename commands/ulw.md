---
name: ulw
description: Ultrawork mode — fully autonomous execution from intent to delivery. Type "ulw" or "ultrawork" anywhere in your prompt, or use /ulw <task>. Skips all human approval gates (design, plan, review, acceptance). Intent Gate classifies your goal first, then routes to the right autonomous path. Does not stop until the task is 100% complete with fresh verification evidence.
---

# ULW — Ultrawork Mode

**One word. Full delivery. No confirmations.**

Ultrawork mode is the fully-autonomous execution path of claude-code-flow. Mention `ulw` or `ultrawork` anywhere in your message to activate it. The system classifies your intent, selects the right pipeline, and runs all the way through — implementation, tests, review, acceptance — without asking for approvals.

## Activation

Any of these work:

```
ulw add a divide function to math.js with tests
ultrawork my login endpoint returns 404, fix it
/ulw refactor the auth module to use repository pattern
/ulw --research how does React Server Components work
```

## How It Works

```
User prompt (with ulw/ultrawork)
    ↓
ulw-detector hook fires → ULW MODE ACTIVE injected
    ↓
Invoke ultrawork skill
    ↓
Intent Gate → classify: implement | fix | refactor | research | explain | test
    ↓
Set mode: autonomous (flow-state.py set-mode autonomous)
    ↓
Activate ralph-loop (continuous execution until done)
    ↓
Execute the right pipeline — all gates auto-approved
    ↓
verification-before-completion with fresh evidence
    ↓
Done. Report with evidence.
```

## Arguments

```
/ulw <task description>
/ulw --research <question>
/ulw --explain <code or concept>
```

- No arguments beyond the task description are required.
- Flags are optional hints to the Intent Gate; omitting them is fine.

## What Gets Skipped

| Gate | Normal Mode | ULW |
|---|---|---|
| Design approval (brainstorm) | User confirms | Auto-approved |
| Plan approval (oracle) | User confirms | Auto-approved |
| Architecture approval (atlas) | User confirms | Auto-approved |
| UI design approval (designer) | User confirms | Auto-approved |
| Review round (sentinel) | User sees result | Auto-handled (max 3 loops) |
| Acceptance (validator) | User sees result | Auto-handled (max 2 loops) |

## What Is Never Skipped

- **Intent Gate** — classify before acting, not after
- **testing-strategy** — write the failing test first, always
- **verification-before-completion** — fresh evidence before marking done
- **Error escalation** — after 3 retries, stop and report to user

## Use When

- You want to go from idea to working code without back-and-forth
- You trust the pipeline and just want results
- Time pressure: ship it now, ask questions later
- Batch of small tasks: `ulw fix all the TypeScript errors`

## Do Not Use When

- The task is ambiguous and you want to discuss options first → use `/brainstorm`
- You need to review the plan before implementation → use `/workflow-plan`
- You want to see the architecture before committing → use `/workflow-plan --mode deep`

## Process

See `ultrawork` skill for the full execution logic.
