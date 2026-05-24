---
name: uli
description: "Ultra Loop Iteration - the single autonomous mode. Type 'uli', legacy 'ulw'/'ultrawork', or /uli <goal>. PD agent proposes requirements each cycle, dev pipeline executes, hard acceptance validates."
argument-hint: "<product goal>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - TaskCreate
  - TaskUpdate
  - Bash(rtk python tests/run-tests.py*)
  - Bash(rtk git status*)
---

# ULI - Ultra Loop Iteration Mode

**Tell it what to build. It iterates until it's done.**

## Activation

```
uli build a CLI tool that generates project scaffolding
ulw add authentication to this app
ultrawork fix the failing login tests
/uli this product needs a working test suite and CI pipeline
```

Everything after `uli`, legacy `ulw`, or `ultrawork` becomes the product goal.

## How It Works

```
User prompt -> uli-detector hook -> ULI MODE ACTIVE -> ultrawork skill
-> Write state + product-state.md
-> Iteration Loop (max 10)
   -> PD: propose requirements
   -> Dev Pipeline: TDD impl
   -> Hard Acceptance: build+test+features
   -> ACCEPT -> next iteration
   -> REJECT -> retry max 2x -> escalate
-> <uli-done>
```

## Legacy Aliases

`ulw` and `ultrawork` now enter ULI. There is no separate ULW stop hook, state file, or completion tag; use `<uli-done>` for autonomous completion.

## Use When

- Autonomous product development over multiple iterations
- Product goal but no specific task breakdowns
- Want system to decide what to build next

## Do Not Use When

- Want to approve plan first -> `/plan`
- Ambiguous, want exploration -> `/brainstorm`

## Process

See `skills/ultrawork/ULI.md` for full execution logic.
