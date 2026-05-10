# Write Spec

Write a feature specification or product requirements document (PRD).

## Workflow

1. **Understand** — Accept feature name, problem statement, user request, or vague idea
2. **Gather context** — Ask conversational: user problem, target users, success metrics, constraints, prior art
3. **Pull from tools** — If connected, search related tickets, research, design docs
4. **Generate PRD** — Produce structured spec (see PRD Structure below)
5. **Review and iterate** — Ask if sections need adjustment, offer follow-up artifacts

## PRD Structure

### Problem Statement
- 2-3 sentences: what problem, who is affected, cost of not solving
- Ground in evidence: user research, support data, metrics, feedback

### Goals
- 3-5 specific, measurable outcomes
- Each answers: "How will we know this succeeded?"
- Outcomes not outputs ("reduce time to first value by 50%" not "build onboarding wizard")

### Non-Goals
- 3-5 things explicitly out of scope
- Brief rationale for each exclusion
- Prevents scope creep during implementation

### User Stories
Standard format: "As a [user type], I want [capability] so that [benefit]"

Guidelines:
- User type should be specific ("enterprise admin" not "user")
- Capability describes what they accomplish, not how
- Benefit explains the why
- Include edge cases and error states
- Order by priority

### Requirements (MoSCoW)
- **P0 Must**: Without these, feature is not viable
- **P1 Should**: Significantly improves experience but core works without
- **P2 Could**: Nice-to-have if time allows, safe to defer
- **P3 Won't (for now)**: Out of scope for v1 but design should support later

### Success Metrics

| Type | Metric | Target | Timeframe |
|------|--------|--------|-----------|
| Leading | Adoption rate | X% | 30 days |
| Lagging | Retention impact | X% | 90 days |

### Open Questions
- Tag each with who should answer (engineering, design, legal, data)
- Distinguish blocking vs non-blocking

### Dependencies
- External services, APIs, or teams this feature depends on
- Technical prerequisites (migrations, infrastructure, library upgrades)
- Cross-team coordination needed

### Timeline Considerations
- Hard deadlines, dependencies, suggested phasing

## Acceptance Criteria Formats

**Given/When/Then**:
- Given [precondition]
- When [action]
- Then [expected outcome]

**Checklist**:
- [ ] Admin can enter SSO provider URL
- [ ] Failed attempts show clear error message

## Scope Management

### Scope Creep Signals
- Requirements added after spec approved
- "Small" additions accumulating
- "While we're at it..." features

### Prevention
- Explicit non-goals in every spec
- Any addition requires a removal or timeline extension
- Clear v1 vs v2 separation
- Time-box investigations: "If we can't figure out X in 2 days, cut it"

## Output Template

```markdown
# [Feature Name] — PRD

**Status:** Draft | In Review | Approved
**Author:** [Name] | **Date:** [Date]

## Problem Statement
[2-3 sentences]

## Goals
1. [Specific measurable outcome]

## Non-Goals
1. [What's out of scope] — [Why]

## User Stories
- As a [user type], I want [capability] so that [benefit]

## Requirements
### P0 — Must-Have
- [Requirement] — AC: [acceptance criteria]

### P1 — Should
- [Requirement]

### P2 — Could
- [Requirement]

### P3 — Won't (for now)
- [Requirement]

## Success Metrics
| Metric | Target | Timeframe |

## Open Questions
| Question | Who | Blocking? |

## Dependencies
- [Prerequisite or external dependency]

## Timeline
- [Phase or deadline]
```

## Tips

1. Be ruthless about P0s — If everything is P0, nothing is P0
2. Non-goals are as important as goals — They prevent scope creep
3. If the idea is too big for one spec — Break into phases and spec the first phase
