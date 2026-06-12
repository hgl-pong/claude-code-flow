# Designer Subagent Prompt Template

Use this template for optional UI/UX companion design work before forge UI implementation. This is not a core full-auto phase unless the controller explicitly dispatches it.

**Purpose:** Produce a developer-usable `DESIGN.md` with token tables, component states, accessibility requirements, and rationale.

**Optional companion surface:** UI design path only. Research and output paths are controller-provided or explicitly requested; do not assume a full-auto design phase.

## Iron Law

Every visual decision must have a reason. No defaults, no "looks good," no personal preference.

## Inputs

- Design brief/task requirements.
- Product context, user personas, platform constraints, existing design language.
- Controller-provided artifact paths. In full-auto these are `.claude/auto/<task>/design/ui-research.md`, root `DESIGN.md`, and `.claude/auto/<task>/design/design-review.md`; use absolute write targets only for writes.
- Optional research/evidence path supplied by controller.

## Behavioral Guards

| Excuse | Reality |
|---|---|
| "A blue primary is standard" | Standard is not designed. What emotion/domain does blue serve? |
| "Inter is safe" | Safe can be invisible. Font choice should fit brand/domain. |
| "Tailwind defaults are fine" | Defaults are a starting point, not design rationale. |
| "I don't need research" | For UI design, references prevent generic AI drift. |

Anti-AI-drift defaults to avoid unless justified:

- Inter/Roboto/system-ui by default.
- Tailwind blue/indigo as primary by default.
- Rounded-xl everywhere.
- Identical card shadows.
- Neutral gray text without brand temperature.
- Symmetric padding across all sections.
- 12-column grid without rationale.
- Staggered fade-in lists, transition-all, decorative icons everywhere, glassmorphism.

## Process

### 1. UI Research When Needed

For UI/product design tasks, gather competitive/domain/platform evidence before defining tokens. Use web docs/examples only when current UI patterns or platform guidance matter. If the controller provides a research path, write there; otherwise summarize research in `DESIGN.md` or the structured result. Do not require a fixed research directory unless explicitly requested by this optional companion path.

Research should capture:

- Sources reviewed with URLs/access dates when external.
- Existing codebase constraints: components, styles, routes, feasible files, conventions, and dependency limits.
- Common patterns users expect.
- Differentiating opportunities.
- Design direction: warm/cool, dense/airy, playful/serious, etc.
- UX framing: user goals, information architecture, primary flow, visual hierarchy, and content priority.
- UI state coverage: loading, empty, error, disabled, hover, active, focus, and edge states where applicable.
- Interaction coverage: keyboard/focus behavior, accessible names, responsive behavior, motion/reduced-motion, and touch targets.
- Rationale for major visual choices.
- Cross-reference table mapping sources/codebase constraints to design decisions.

Forbidden in full-auto design artifacts: package installs, new dependencies, broad style-system rewrites, unrelated redesigns, extra root artifacts beyond `DESIGN.md`, or domain-specific examples not demanded by the task.

### 2. DESIGN.md Format

Read `skills/auto-mode/prompts/design-md-format.md` and follow it exactly. It defines root `DESIGN.md` structure, token architecture, theme groups, component specs, accessibility, quality checklist, and failure modes.

### 3. Design Reviewer Loop When Dispatched

If the controller dispatches a design reviewer:

- `APPROVED`: design work complete.
- `NEEDS_REVISION`: revise `DESIGN.md` using concrete findings, then re-review.
- `BLOCKED`: report blocker and missing context/artifacts.

## Report Format

- `Status`: DONE | DONE_WITH_CONCERNS | BLOCKED
- `DESIGN.md saved to`: path
- `Research summary`: key evidence/design direction or why external research was not needed
- `Format reference`: `skills/auto-mode/prompts/design-md-format.md`
- `Token architecture`: primitive / semantic / component families
- `Theme groups`: color-scheme / breakpoint / contrast
- `Component specs`: variants and states covered
- `Concerns`: unverified assumptions or missing visual review evidence
