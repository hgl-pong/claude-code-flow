---
name: Executing Plans
version: "1.0.0"
description: "Use when you have a written implementation plan to execute in the current session"
argument-hint: "<plan to execute>"
---

# Executing Plans

## Overview

Load plan, review critically, execute all tasks, report when complete.

**Core principle:** Follow plan steps exactly. Don't skip verifications. Stop when blocked.

## Process

### Step 1: Load and Review

1. Read plan file
2. Review critically — identify questions or concerns
3. If concerns: raise with user before starting
4. If no concerns: create TaskCreate for all tasks and proceed

### Step 2: Execute Tasks

For each task:

1. Mark in_progress
2. Follow each step exactly (plan has bite-sized steps)
3. Run verifications as specified
4. Use prompt templates from `dev-orchestrator/references/subagent-prompts.md` for agent dispatch
5. Mark completed

### Step 3: Complete

After all tasks verified:
- Invoke `finishing-branch` to handle merge/PR/cleanup
- Use `verification-before-completion` before claiming done

## When to Stop

**STOP immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing progress
- Don't understand an instruction

**Ask for clarification rather than guessing.**

## Prompt Requirements

Every dispatch must include:
- Goal, task, working directory, completed dependencies, exact file scope
- Exact test command and acceptance criteria
- Relevant plan/design/code excerpts (paste directly — never ask subagents to "read the plan")
- Explicit out-of-scope files or behaviors
- Required `FILES_MODIFIED` declaration

## Red Flags

- Skipping a verification step because "it's obvious"
- Adapting the plan without discussing with user
- Proceeding when blocked instead of asking for help
- Trusting agent success reports without checking FILES_MODIFIED
- Starting implementation on main/master without explicit user consent

## Integration

- **REQUIRED:** `verification-before-completion` — verify before claiming done
- **SUGGESTED:** `finishing-branch` — complete development after all tasks
- **SUGGESTED:** `dispatching-parallel-agents` — for tasks with independent file scopes
