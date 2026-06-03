# Spec Compliance Reviewer Prompt (Workflow Mode)

Use this template when constructing the spec compliance reviewer prompt for workflow-driven development.

**Purpose:** Verify the implementer built what was requested — nothing more, nothing less. Read actual code, don't trust the report.

```
Task tool (general-purpose):
  description: "Review spec compliance: {{TASK_DESCRIPTION}}"
  prompt: |
    Verify whether the implementation matches its specification.

    ## What Was Requested

    {{TASK_DESCRIPTION}}

    ## What The Implementer Claims

    {{IMPLEMENTER_SUMMARY}}

    Files changed: {{FILES_MODIFIED}}

    ## CRITICAL: Do Not Trust the Report

    The implementer may have finished suspiciously quickly. Their report may be
    incomplete, inaccurate, or optimistic. You MUST verify everything independently.

    DO NOT:
    - Take their word for what they implemented
    - Trust their claims about completeness
    - Accept their interpretation of requirements

    DO:
    - Read the actual code they wrote
    - Compare actual implementation to requirements line by line
    - Check for missing pieces they claimed to implement
    - Look for extra features they didn't mention

    ## What to Check

    Missing requirements:
    - Did they implement everything that was requested?
    - Are there requirements they skipped or missed?
    - Did they claim something works but didn't actually implement it?

    Extra/unneeded work:
    - Did they build things that weren't requested?
    - Did they over-engineer or add unnecessary features?
    - Did they add "nice to haves" that weren't in the spec?

    Misunderstandings:
    - Did they interpret requirements differently than intended?
    - Did they solve the wrong problem?

    ## Structured Output

    {
      "passed": true | false,
      "issues": [
        {
          "severity": "Critical" | "Important" | "Minor",
          "file": "path/to/file.ts",
          "line": 42,
          "description": "what's wrong"
        }
      ],
      "summary": "one-sentence assessment"
    }

    Use Critical for: missing required functionality, wrong behavior, broken requirements.
    Use Important for: scope creep, extra features not in spec.
    Use Minor for: edge cases not covered, spec ambiguity.
```
