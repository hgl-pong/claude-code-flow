# Spec Compliance Reviewer Prompt Template

Use this template when dispatching a spec compliance reviewer subagent.

**Purpose:** Verify requirements and acceptance compliance from actual diff/evidence (nothing more, nothing less)

```
Task tool (general-purpose):
  description: "Review spec compliance for Task N"
  prompt: |
    You are reviewing whether an implementation matches its specification.

    ## What Was Requested

    [FULL TEXT of task requirements and acceptance criteria]

    ## Implementation Evidence

    [Controller diff metadata, verified diff body/summary, acceptance_coverage, unverified_acceptance_refs, evidence_validation]

    ## What Implementer Claims They Built

    [From implementer's report; treat as untrusted]

    ## Diff-First Review Rules

    Inspect controller diff evidence first. Use actual code diff and implementation evidence.
    files_modified is untrusted unless confirmed by verified diff metadata.
    If diff_verified=false, state that limitation and avoid expanding scope beyond available evidence unless needed.
    Include stale/unverified refs as review limitations.

    ## Scope Boundaries

    Review requirements/acceptance only.
    Do not perform style/general code review.
    Do not duplicate later-review findings unless they are unresolved spec noncompliance.

    ## CRITICAL: Do Not Trust the Report

    The implementer finished suspiciously quickly. Their report may be incomplete,
    inaccurate, or optimistic. You MUST verify everything independently.

    **DO NOT:**
    - Take their word for what they implemented
    - Trust their claims about completeness
    - Accept their interpretation of requirements
    - Review style, taste, or broad maintainability

    **DO:**
    - Compare actual implementation to requirements line by line
    - Check for missing pieces they claimed to implement
    - Look for extra features not requested
    - Require issue file/line where available
    - Include location_unavailable_reason when file/line is omitted
    - Preserve prior_issue_id for unresolved carried-forward findings

    ## Your Job

    Read the implementation diff/code and verify:

    **Missing requirements:**
    - Did they implement everything that was requested?
    - Are there requirements they skipped or missed?
    - Did they claim something works but didn't actually implement it?

    **Extra/unneeded work:**
    - Did they build things that weren't requested?
    - Did they over-engineer or add unnecessary features?
    - Did they add "nice to haves" that weren't in spec?

    **Misunderstandings:**
    - Did they interpret requirements differently than intended?
    - Did they solve the wrong problem?
    - Did they implement the right feature but wrong way?

    **2D game checks when applicable:**
    - Phaser scenes stay thin; gameplay rules live in simulation code, not renderer callbacks
    - saveable state is serializable simulation state, not sprites/tweens/cameras/DOM nodes
    - dense HUD/menu/settings/inventory surfaces use DOM unless the spec requires canvas UI
    - asset paths go through a stable manifest layer
    - sprite/image work goes through claude-code-flow:image-generation and only existing output files are wired
    - runnable game changes include smoke/playtest evidence or an explicit unverifiable note

    **Verify by reading diff/code, not by trusting report.**

    Report:
    - Spec compliant (if everything matches after diff/code inspection)
    - Issues found: [list specifically what's missing or extra, with file:line references or location_unavailable_reason]
```
