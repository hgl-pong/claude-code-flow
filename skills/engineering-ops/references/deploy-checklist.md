# Deploy Checklist

Generate a structured verification checklist before deploying to production. Adapt phases to the specific release type.

## Phase 1: Pre-Deploy

```markdown
## Pre-Deploy Verification

### Tests
- [ ] All unit tests pass
- [ ] Integration tests pass (relevant subset)
- [ ] E2E tests pass (critical paths)
- [ ] No test skips without documented reason

### Code Review
- [ ] All changes reviewed and approved
- [ ] No outstanding review comments (resolved or deferred with ticket)
- [ ] Sentinel review completed (if workflow active)

### Known Bugs
- [ ] No SEV1/SEV2 bugs open against this release
- [ ] Known SEV3/SEV4 bugs documented and accepted
- [ ] Bug count trend acceptable (not increasing)

### Database Migrations (if applicable)
- [ ] Migration tested forward and rollback on staging
- [ ] Migration is non-blocking (no table locks on large tables)
- [ ] Data backfill script ready (if schema change)
- [ ] Migration separate from code deploy (if risky)

### Feature Flags (if applicable)
- [ ] New flags registered in flag system
- [ ] Default state documented (on/off)
- [ ] Flag cleanup ticket created
- [ ] Flags tested in both states

### Rollback Plan
- [ ] Rollback procedure documented
- [ ] Previous artifact version identified
- [ ] Rollback tested on staging
- [ ] Data backward compatibility verified
```

## Phase 2: Deploy

```markdown
## Deploy Execution

### Staging
- [ ] Deploy to staging
- [ ] Smoke tests pass on staging
- [ ] Staging mirrors production config

### Production Canary
- [ ] Deploy to canary / single instance
- [ ] Monitor error rate for [X] minutes
- [ ] Monitor latency p50/p95/p99
- [ ] Verify logs for unexpected warnings

### Production Full Rollout
- [ ] Roll out to full production
- [ ] Verify health checks pass
- [ ] Verify key user flows manually (smoke)
- [ ] Monitor dashboards for [X] minutes
```

## Phase 3: Post-Deploy

```markdown
## Post-Deploy Verification

### Metrics
- [ ] Error rate within baseline
- [ ] Latency within baseline
- [ ] Resource usage (CPU, memory, disk) stable
- [ ] No new alert firing

### Documentation
- [ ] Changelog updated
- [ ] Release notes published
- [ ] API docs updated (if API changes)

### Communication
- [ ] Team notified of deployment
- [ ] Stakeholders informed (if user-facing)
- [ ] Related tickets moved to Done

### Cleanup
- [ ] Temporary flags/migrations scheduled for removal
- [ ] Monitoring thresholds reviewed and adjusted
```

## Rollback Triggers

| Metric | Threshold | Action |
|--------|-----------|--------|
| Error rate | > 2x baseline (sustained 5 min) | Immediate rollback |
| Latency p99 | > 3x baseline | Investigate, rollback if no fix in 10 min |
| Crash rate | > 1% of instances | Immediate rollback |
| Customer reports | > 3 independent reports | Investigate, prepare rollback |

## Customization

Adapt the checklist based on release type:

- **Feature flags** -- Add flag verification steps in both on/off states
- **DB migration** -- Add forward/rollback migration checks, data integrity verification
- **Breaking API change** -- Add consumer notification, version negotiation, deprecation timeline
- **Config change** -- Add config validation, diff review, restart verification
- **Hotfix** -- Skip staging, go directly to canary with abbreviated checklist

## If Connectors Available

If **~~code-intel** is connected:
- Use `gitnexus_impact` to verify the PR diff blast radius matches expected scope
- Use `gitnexus_query` to find execution flows affected by the changes

## Tips

1. **Time-box monitoring.** Define how long you watch after deploy before declaring success. Five minutes is not enough for most services; 30-60 minutes catches most regressions.
2. **Test the rollback, not just the deploy.** A rollback you haven't tested is a rollback that will fail when you need it most. Include rollback verification in staging.
3. **Separate risky changes.** DB migrations, config changes, and code deploys should be separate steps when any of them carry risk. Combined deploys make rollback ambiguous.
