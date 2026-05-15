# Incident Response

Structured workflow for handling production incidents from triage through postmortem. Follow the phases in order.

## Severity Classification

| Level | Name | Criteria | Response Time |
|-------|------|----------|---------------|
| SEV1 | Critical | Service down, data loss, security breach, widespread user impact | Immediate |
| SEV2 | Major | Significant feature broken, degraded performance, partial user impact | < 30 min |
| SEV3 | Minor | Non-critical feature impaired, workaround available | < 4 hours |
| SEV4 | Low | Cosmetic issue, minor inconvenience, no user impact | Next business day |

## Phase 1: Triage

```markdown
## Incident Triage

### Severity Assessment
- Severity: [SEV1 / SEV2 / SEV3 / SEV4]
- Affected systems: [list]
- Affected users: [percentage or count]
- Business impact: [revenue / reputation / compliance]

### Role Assignment
- Incident Commander: [name] -- owns coordination, not debugging
- Technical Lead: [name] -- owns investigation and fix
- Communicator: [name] -- owns status updates

### Initial Actions
- [ ] Acknowledge the alert
- [ ] Open war room / communication channel
- [ ] Set severity and assign roles
- [ ] Start timeline document
- [ ] Page additional on-call if needed
```

## Phase 2: Communicate

```markdown
## Status Update Template

**[SEV LEVEL] - [INCIDENT TITLE]**
Time: [UTC timestamp]
Status: [Investigating / Mitigating / Monitoring / Resolved]

### Impact
[What users are experiencing, in plain language]

### Current Status
[What we know, what we are doing]

### ETA for Next Update
[When stakeholders can expect the next update, typically every 15-30 min for SEV1]

### Timeline
- HH:MM UTC -- Alert triggered
- HH:MM UTC -- Incident declared, roles assigned
- HH:MM UTC -- [action taken]
- HH:MM UTC -- [finding or mitigation applied]
```

## Phase 3: Mitigate

```markdown
## Mitigation Checklist

### Investigation
- [ ] Reproduce the issue (if safe to do so)
- [ ] Check recent deployments and changes
- [ ] Review logs, metrics, and traces
- [ ] Identify root cause or proximate cause

### Mitigation Actions
- [ ] Apply mitigation (rollback, feature flag off, scale up, failover)
- [ ] Document each action with timestamp
- [ ] Verify mitigation is effective

### Confirmation
- [ ] Error rates return to baseline
- [ ] Latency returns to baseline
- [ ] User reports stop or decrease
- [ ] Monitor for [X] minutes before declaring resolved
```

## Phase 4: Postmortem

```markdown
## Postmortem Template

### Incident Summary
- **Date**: YYYY-MM-DD
- **Duration**: X hours Y minutes
- **Severity**: SEV[X]
- **Impact**: [user count, revenue, systems affected]

### Timeline
| Time (UTC) | Event |
|------------|-------|
| HH:MM | Alert triggered |
| HH:MM | Incident declared |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Resolved |

### Root Cause (5 Whys)

1. **Why did the incident occur?** [direct cause]
2. **Why did [direct cause] happen?** [underlying cause]
3. **Why did [underlying cause] happen?** [systemic cause]
4. **Why did [systemic cause] happen?** [process cause]
5. **Why did [process cause] happen?** [organizational cause]

### What Went Well
- [List things that worked during the incident response]

### What Went Poorly
- [List things that didn't work or caused delays]

### Action Items

| Action | Owner | Priority | Ticket |
|--------|-------|----------|--------|
| [specific action] | [name] | P1/P2/P3 | [link] |

### Lessons Learned
[2-3 sentences capturing the key takeaway]

**This postmortem is blameless.** Focus on systems and processes, not individuals.
```

## If Connectors Available

If **~~code-intel** is connected:
- Use `gitnexus_query` to find execution flows related to failing components
- Use `gitnexus_context` to trace the call chain from error surface to root cause
- Use `gitnexus_impact` to assess blast radius before applying mitigations

## Tips

1. **Mitigate first, fix second.** During an active incident, prioritize restoring service over finding the perfect fix. A rollback is better than a 2-hour investigation while users are down.
2. **Keep the timeline running.** Every action gets a timestamp. The timeline is the most valuable artifact for the postmortem. If you didn't write it down, it didn't happen.
3. **Blameless does not mean accountability-free.** Postmortems identify systemic improvements without pointing fingers at people. Action items must have owners, deadlines, and tickets.
