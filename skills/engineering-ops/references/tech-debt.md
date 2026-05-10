# Tech Debt Assessment

## Debt Categories

| Category | Examples | Signals |
|----------|----------|---------|
| Code | Duplication, poor abstractions, god classes | High cyclomatic complexity, copy-paste patterns |
| Architecture | Monolith creep, wrong data store, tight coupling | Circular dependencies, cross-module imports |
| Test | Low coverage, flaky tests, no integration tests | Test skip counts, CI flake rate |
| Dependency | Outdated packages, unmaintained libs, version pinning | Known CVEs, >2 major versions behind |
| Documentation | Missing runbooks, tribal knowledge, stale READMEs | Onboarding time, repeated questions |
| Infrastructure | Manual deploys, no monitoring, snowflake servers | Deploy frequency, MTTR |

## Prioritization

Score each debt item on three axes (1-5):

- **Impact** -- How much does this slow development or increase risk?
- **Risk** -- Likelihood of causing incidents or data loss?
- **Effort** -- How many engineer-days to remediate?

Formula:

```
Priority = (Impact + Risk) x (6 - Effort)
```

Higher score = higher priority. Quick wins (low effort, high impact/risk) surface naturally.

## Assessment Process

1. **Scan** the target area -- read code, check test coverage, review dependency versions
2. **Catalog** every debt item with category, location, and brief description
3. **Score** each item using the formula above
4. **Group** into tiers:
   - **P0 -- Critical**: Active incidents or imminent risk (fix now)
   - **P1 -- High**: Blocks feature work or causes frequent bugs (next sprint)
   - **P2 -- Medium**: Slows development but not blocking (plan this quarter)
   - **P3 -- Low**: Nice to have, no urgency (backlog)

## Output Template

```markdown
# Tech Debt Assessment: [Area]

## Summary
- Total items: N
- Critical (P0): N | High (P1): N | Medium (P2): N | Low (P3): N
- Estimated remediation: N engineer-weeks

## Critical (P0)
| # | Category | Location | Description | Impact | Risk | Effort | Score |
|---|----------|----------|-------------|--------|------|--------|-------|
| 1 | ... | ... | ... | ... | ... | ... | ... |

## Remediation Plan
### Phase 1 -- Immediate (Week 1-2)
- [ ] Item 1: [business justification]
- [ ] Item 2: [business justification]

### Phase 2 -- Short-term (Month 1)
- [ ] Item 3: [business justification]

### Phase 3 -- Long-term (Quarter)
- [ ] Item 4: [business justification]
```

Every item in the remediation plan must include a **business justification** -- not "cleaner code" but "reduces deploy failures by 40%" or "unblocks the payments feature."

## If Connectors Available

If **~~code-intel** is connected:
- Run symbol impact analysis before scoring debt items -- upstream dependency maps validate risk scores
- Use `gitnexus_impact` on proposed refactoring targets to estimate true effort (blast radius = effort proxy)

## Tips

- Run a full audit quarterly; spot-check specific areas after major feature work.
- Prefer "good enough" remediation over perfect refactoring -- a 70% improvement shipped beats a 100% plan that never executes.
- Tie every P0/P1 item to a concrete cost: "this flaky test wastes 2 hrs/week of CI time."
