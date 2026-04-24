---
name: workflow-evolve
description: Analyze workflow execution logs and propose prompt improvements. Review and approve/reject evolution proposals.
---

# Workflow Evolve

Analyze past workflow executions and manage prompt improvement proposals.

## Process

1. Check if `.claude/flow/exec-log.jsonl` exists and has data. If not, report "No execution data yet. Complete at least one full workflow first."

2. **Analyze**: Invoke the evolver agent to scan logs and generate proposals:
   ```
   Agent({
     name: "evolver",
     subagent_type: "claude-code-flow:evolver",
     model: "opus",
     prompt: "Analyze workflow execution logs and propose prompt improvements. Write proposals to .claude/flow/evolution-pending.md"
   })
   ```

3. **Review proposals**: Read `.claude/flow/evolution-pending.md` and present each proposal to the user with:
   - What agent/file it affects
   - The specific change (before/after)
   - Expected effect
   - Risk level

4. **User decision**: For each proposal, ask the user to:
   - **Approve**: Apply the change
   - **Reject**: Discard the proposal
   - **Defer**: Keep for later review

5. **Apply approved proposals**: For each approved proposal:
   - Run `python hooks/scripts/eval-gate.py validate-prompt-change <agent_file>` to validate
   - If PASS: apply the change to the agent file
   - If WARN: confirm with user before applying
   - If FAIL: report why and skip
   - Create a backup of the original file before modifying
   - Move applied proposals to `.claude/flow/evolution-history.md`

## Usage

```
/workflow-evolve
```

## Notes

- The evolver needs at least 3-5 completed workflow sessions to produce meaningful proposals
- Proposals are suggestions only — nothing is applied without user approval
- Each approved change is backed up before application
- Run periodically (e.g., weekly) to catch emerging patterns
