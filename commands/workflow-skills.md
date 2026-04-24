---
name: workflow-skills
description: Manage the skill library — view current skills, review proposals for new skills, and approve or reject them.
---

# Workflow Skills

Manage the workflow skill library — view, detect, and create skills.

## Process

1. **Show current library**: Run `python hooks/scripts/skill-detector.py stats` and `python hooks/scripts/skill-detector.py list`

2. **Detect new skill needs**: Run `python hooks/scripts/skill-detector.py detect` to analyze unmatched tasks and propose new skills

3. **Review proposals**: If `.claude/flow/skill-proposals.md` exists, read it and present each proposal to the user:
   - What keywords/patterns triggered the proposal
   - How many unmatched tasks matched
   - Example task descriptions
   - Suggested agent assignment

4. **User decision**: For each proposal:
   - **Approve**: Create a new skill entry in `skill-seeds.json` and optionally create a `skills/<name>/SKILL.md`
   - **Reject**: Discard the proposal
   - **Defer**: Keep for later

## Skill Creation

When approving a new skill:
1. Add entry to `.claude/flow/skill-seeds.json` with appropriate trigger_patterns
2. Optionally create `skills/<name>/SKILL.md` with a detailed skill definition
3. Run `python hooks/scripts/eval-gate.py validate-skill skills/<name>/SKILL.md` if a skill file is created

## Usage

```
/workflow-skills
```

## Notes

- Skills are matched against user task descriptions during workflow planning
- The system learns from unmatched tasks — the more workflows you run, the better it gets at detecting new skill needs
- Skills can also be created manually by editing `skill-seeds.json`
