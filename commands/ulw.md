---
name: ulw
description: "Fully autonomous execution. Type 'ulw' or 'ultrawork' in prompt, or /ulw <task>. Intent Gate classifies goal, then routes to autonomous pipeline. No confirmations until done."
---

# ULW — Ultrawork Mode

**One word. Full delivery. No confirmations.**

## Activation

```
ulw add a divide function to math.js with tests
ultrawork my login endpoint returns 404, fix it
/ulw refactor the auth module to use repository pattern
```

## How It Works

```
User prompt → ulw-detector hook → ULW MODE ACTIVE → ultrawork skill
→ Intent Gate (implement|fix|refactor|research|explain|test)
→ autonomous mode → ralph-loop → execute pipeline → verify → <ulw-done>
```

## Use When

- Idea to working code without back-and-forth
- Trust the pipeline, just want results
- Time pressure: ship it now
- Batch of small tasks

## Do Not Use When

- Ambiguous task, want to discuss options → `/brainstorm`
- Need to review plan first → `/plan`
- Want to see architecture first → `/plan --mode deep`

## Process

See `ultrawork` skill for full execution logic.
