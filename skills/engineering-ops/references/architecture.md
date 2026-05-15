# Architecture Decision Records

Use this skill when making significant technology choices, evaluating competing approaches, or designing new system components. Produces structured ADRs or system design documents.

## Modes

### 1. Create ADR

Document a decision that has been made or is being proposed.

```markdown
## ADR: [NUMBER] - [TITLE]

### Status
[Proposed | Accepted | Deprecated | Superseded by ADR-XXX]

### Date
YYYY-MM-DD

### Deciders
[List everyone who was involved in or approves this decision]

### Context
[What is the issue that we're seeing that is motivating this decision or change?
Include technical and business constraints. State the forces at play.]

### Decision
[What is the change that we're proposing and/or doing? One sentence, decisive.]

### Options Considered

| Aspect | Option A: [Name] | Option B: [Name] | Option C: [Name] |
|--------|------------------|------------------|------------------|
| Description | [brief] | [brief] | [brief] |
| Pros | [list] | [list] | [list] |
| Cons | [list] | [list] | [list] |
| Effort | [estimate] | [estimate] | [estimate] |
| Risk | [low/med/high] | [low/med/high] | [low/med/high] |

### Trade-off Analysis
[For the chosen option, explicitly state what you are gaining and what you are giving up.]

- Gaining: ...
- Giving up: ...
- Mitigation for what we give up: ...

### Consequences
[What becomes easier or more difficult to do because of this change?]

- Positive: ...
- Negative: ...
- Neutral: ...

### Action Items
- [ ] [Implementation step 1]
- [ ] [Implementation step 2]
- [ ] [Update documentation]
- [ ] [Communicate to team]
```

### 2. Evaluate Design

Review an existing design or proposal. Assess against requirements, identify gaps, and recommend improvements.

Evaluation checklist:
- Does it meet stated functional requirements?
- Does it address non-functional requirements (performance, security, reliability)?
- Are failure modes identified and handled?
- Is the design consistent with existing architecture?
- Are dependencies justified and minimal?
- Is there a clear rollback path?

### 3. System Design

Design a new component or system. Follow this framework:

1. **Requirements Gathering** -- Functional requirements, non-functional requirements, constraints, assumptions
2. **High-Level Design** -- Component diagram, data flow, API contracts, ownership boundaries
3. **Deep Dive** -- Data model, algorithms, error handling, state management
4. **Scale and Reliability** -- Bottlenecks, caching strategy, redundancy, monitoring, graceful degradation
5. **Trade-off Analysis** -- Speed vs. correctness, consistency vs. availability, complexity vs. flexibility

## If Connectors Available

If **~~code-intel** is connected:
- Use `gitnexus_query` to search for prior ADRs and related design decisions in the codebase
- Use `gitnexus_impact` to check blast radius of proposed architectural changes
- Use `gitnexus_context` to understand current dependencies before designing new components

## Tips

1. **State constraints upfront.** Budget, timeline, team skills, and existing infrastructure are as important as technical trade-offs. A technically superior option that the team can't maintain is the wrong choice.
2. **Name your options.** Don't leave "Option A" as the final name. Give each option a descriptive label that captures its essence (e.g., "Event-Driven with Kafka" vs "Polling with Cron").
3. **Include non-functional requirements.** Latency targets, throughput needs, uptime SLAs, and data retention policies often determine the right architecture more than feature requirements.
