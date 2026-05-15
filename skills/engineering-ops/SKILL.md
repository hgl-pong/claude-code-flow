---
name: Engineering Ops
version: "1.0.0"
description: "Consolidated engineering operations skill. Trigger with 'architecture decision', 'ADR for', 'evaluate this design', 'system design for', 'should we use X or Y', 'deploy checklist', 'pre-deploy', 'shipping checklist', 'release checklist', 'ready to deploy', 'we have an incident', 'production is down', 'SEV1/SEV2', 'postmortem', 'blameless review', 'tech debt', 'technical debt audit', 'what should we refactor', 'code health', 'refactoring priorities', 'standup', 'daily update', 'what did I do yesterday', 'status update', 'write docs for', 'document this', 'create a README', 'write a runbook', 'onboarding guide', 'API docs'."
argument-hint: "[architecture | deploy | incident | tech-debt | standup | docs] <context>"
---

# Engineering Ops

Dispatch skill for engineering operations. Identify the requested mode or auto-detect from context.

## Modes

| Mode | Trigger | Description | Reference |
|------|---------|-------------|-----------|
| **architecture** | ADR, system design, evaluate design, should we use X or Y | Create ADRs, evaluate designs, or produce system design documents | `references/architecture.md` |
| **deploy** | deploy checklist, pre-deploy, shipping checklist, release checklist | Generate structured pre-deploy/deploy/post-deploy verification checklists | `references/deploy-checklist.md` |
| **incident** | incident, production is down, SEV1/SEV2, postmortem, blameless | Run incident response from triage through postmortem | `references/incident-response.md` |
| **tech-debt** | tech debt, refactor priorities, code health, audit | Identify, categorize, and prioritize technical debt with remediation plan | `references/tech-debt.md` |
| **standup** | standup, daily update, what did I do, status update | Generate standup report from git history or raw notes | `references/standup.md` |
| **docs** | write docs, document this, README, runbook, API docs | Write READMEs, API docs, runbooks, architecture docs, onboarding guides | `references/documentation.md` |

## Dispatch Logic

1. Match user input to a mode from the table above
2. If ambiguous, ask which mode
3. Load the corresponding reference file from the table's Reference column
4. Execute the workflow described in the reference

For each mode, see **references/<topic>.md** for detailed workflow, templates, and output formats.

## Reference Files

- `references/architecture.md` — ADR template, design evaluation, system design workflow
- `references/deploy-checklist.md` — Pre-deploy/deploy/post-deploy checklist with rollback triggers
- `references/incident-response.md` — Severity levels, incident phases, postmortem template
- `references/tech-debt.md` — Audit framework, scoring formula, prioritization tiers
- `references/standup.md` — Standup formats (Auto-Pull, Freeform, Retro), git-based reporting
- `references/documentation.md` — README, API docs, runbooks, architecture docs, onboarding guides

## If Connectors Available

If **~~code-intel** is connected:
- `gitnexus_query` -- search for prior ADRs, execution flows, related decisions
- `gitnexus_impact` -- blast radius of proposed changes, refactoring targets, deploy diffs
- `gitnexus_context` -- trace dependencies, call chains, symbol relationships

If **~~browser** is connected:
- Run post-deploy smoke tests: navigate to key pages, verify content renders, screenshot evidence
- Automate deploy verification: click through critical flows, check for console errors

## Tips

1. **Start with the mode.** If unsure which mode, scan the trigger phrases — the user's wording usually maps directly.
2. **Load only the needed reference.** Don't load all six reference files at once; read the one for the detected mode.
3. **Chain modes when needed.** An incident postmortem may trigger a tech-debt audit. A deploy checklist may reference architecture decisions. Load the second reference when the workflow crosses boundaries.
