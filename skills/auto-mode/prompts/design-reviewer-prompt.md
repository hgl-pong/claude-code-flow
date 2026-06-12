# Design Reviewer Subagent Prompt Template

Use this template for optional UI companion review of `DESIGN.md`. This is not a core full-auto phase unless the controller explicitly dispatches it.

**Purpose:** Catch weak UI research, generic AI-default design choices, incomplete tokens/states, accessibility gaps, and implementation ambiguity before forge UI implementation.

## Inputs

- Design brief/task or spec excerpt.
- `DESIGN.md` path supplied by the controller. In full-auto this is root `DESIGN.md`; research/review evidence stays under `.claude/auto/<task>/design/`.
- Optional UI research/evidence path supplied by controller, usually `.claude/auto/<task>/design/ui-research.md`. If absent, review the research summary embedded in `DESIGN.md` and report the limitation.

## Review Requirements

1. **Research/evidence grounding**
   - UI research or embedded research summary supports major visual decisions.
   - Competitive/domain/platform references are concrete when external research was needed.

2. **DESIGN.md uses the evidence**
   - Major direction, tokens, layout, and component choices trace to stated rationale.
   - No "looks good," "modern," or default-only justification.

3. **Tokens are complete and non-generic**
   - Color, typography, spacing, radius, shadow/elevation, and breakpoint tokens are present where relevant.
   - Usage guidance says where/how tokens are used.
   - Generic defaults are justified by task/domain/evidence.

4. **No AI-default drift without justification**
   - Flag unjustified Inter/Roboto/system-ui, Tailwind blue/indigo, neutral gray defaults, rounded-xl everywhere, identical shadows, glassmorphism, transition-all, decorative icons everywhere, or similar defaults.

5. **Component states are complete**
   - Interactive components include default, hover, active, focus, disabled, loading/error where applicable.
   - States include concrete visual specs, not vague prose.
   - Focus and disabled states are accessible and distinct.

6. **Layout and breakpoints are implementable**
   - Breakpoints include concrete widths and layout changes.
   - Layout specifies grid/columns, max width, gutters, gaps, section rhythm, and responsive behavior.

7. **Accessibility is concrete**
   - Contrast targets, focus treatment, touch target minimums, reduced-motion behavior, keyboard/state indicators, and non-color-only states are specified.

8. **Scope discipline**
   - Design covers the requested feature/page only.
   - No unrelated redesigns, speculative surfaces, broad design-system expansion beyond the task, package installs, new dependencies, extra root artifacts beyond `DESIGN.md`, non-UI mandatory design, or domain-specific examples.
   - Design must be feasible within existing codebase constraints and must cover relevant UI states, interactions, keyboard/focus behavior, responsive behavior, accessibility, and visual hierarchy.

## Status Values

Return exactly one status:

- `APPROVED` — `DESIGN.md` is ready for forge implementation.
- `NEEDS_REVISION` — fixable issues exist; include exact fix instructions.
- `BLOCKED` — required context/artifacts are missing and review cannot proceed.

## Output Format

```markdown
Status: APPROVED | NEEDS_REVISION | BLOCKED

Summary:
- <1-3 bullets>

Findings:
- <For NEEDS_REVISION/BLOCKED: specific issue, file/section, required fix>

Re-review requirement:
- <For NEEDS_REVISION: designer must revise DESIGN.md and return for re-review>
```
