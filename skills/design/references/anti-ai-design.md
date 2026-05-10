# Anti-AI-Design Rules

AI-generated UI looks like every other AI-generated UI. These rules exist to prevent that.

Shared by: `ui-design` skill (design phase) and `forge` agent (implementation phase).

---

## Banned Elements — require explicit written justification to use

If you use any of these without justification, the output will be flagged as AI-generic:

| Element | Why it's banned | What to do instead |
|---------|----------------|-------------------|
| Blue-purple gradient hero/accent | Every AI design uses it | Pick a palette specific to this product's domain and tone |
| Glassmorphism / frosted-glass cards | Visual trend with no functional benefit | Use surface elevation through color difference, not blur |
| Gradient text on metrics or numbers | The AI "premium data" cliche | Bold weight + color contrast for emphasis |
| Identical card grid (Card > Image > Title > Description > CTA) | The template layout | Use 2-3 card variants with different content density: feature cards (image + title + body), stat cards (number + label), action cards (icon + title + arrow) |
| Bounce / elastic easing on more than one element | "Playful" default that reads as template | Custom cubic-bezier per interaction type |
| Fade-in-on-scroll on every section | Adds no meaning, reads as filler animation | Reserve scroll-triggered animation for one intentional moment |
| Cards nested inside cards (two+ levels of nesting) | Structural laziness | Use whitespace, borders, or typographic hierarchy instead. One level of containment (section card with form fields) is acceptable |
| Inter + Roboto + system-sans with zero customization | The AI font stack | Pick one font with character; pair it deliberately |
| Pure `#9ca3af` / `#6b7280` (Tailwind gray-400/500) | Neutral gray is a reset to template | Tint all grays: add 4-8% warm or cool hue |
| Shadow on every card/container | "Elevated" default | Use either shadow or border, not both, not everywhere |
| `rounded-xl` on everything | One-size radius is a template signal | Vary radii: inputs differ from cards, cards differ from modals |
| Five "equal" brand colors | No visual hierarchy | One dominant surface, one sharp accent, rest are neutrals |
| `primary` / `accent-500` / `secondary` token names | Generic naming = generic thinking | Semantic names: `surface-canvas`, `text-heading`, `interaction-focus` |
| `#3B82F6` (Tailwind blue-500) or `#6366F1` (indigo-500) as primary | THE most common AI colors | Choose by domain and emotional intent, not by framework default |
| Blue-family or purple-family primary without justification | The AI "premium" default | Domain-specific: teal (fintech), amber (creative), cyan (devtools), coral (health) |

## Layout Anti-Patterns

These are structural tells that a layout was generated, not designed:

- **Hero → Features Grid → CTA → Footer** (the AI template sequence — break the order)
- **Every section centered and symmetric** (asymmetry signals intentionality)
- **Identical padding on all sections** (`64px → 64px → 64px` is repetition, not rhythm)
- **All headings the same visual weight** (scale contrast IS design — vary it)
- **Sections that could be swapped in any order** (each section should earn its position)
- **Three equal columns of cards** (vary width, content, or layout per column)
- **Every icon the same size** (important icons bigger, decorative icons smaller)
- **Perfect center alignment of every element** (offset creates visual interest)

## Section Template Anti-Patterns

These section types are so consistently AI-generated they read as template signals:

- **Three-tier pricing table** with middle tier "highlighted" — break the pattern: show pricing inline, use a toggle instead, or design a single-tier value prop
- **Testimonial row** (avatar circle + quote + name, repeated 3x) — use ONE detailed case study instead of three shallow ones
- **Trust logo strip** (partner logos at reduced opacity) — if you must, integrate logos into context, not a standalone row
- **"Why choose us" feature comparison** (checkmark vs X grid) — let the product speak, not a comparison table
- **"Our Process" three-step numbered** (01 Discover, 02 Design, 03 Deliver with connecting lines) — if the process isn't the actual user journey, remove it. If it is, present as a workflow artifact (timeline, kanban, branching flowchart), not decorative numbering
- **FAQ accordion** with chevron icons — use contextual help in the UI instead, or a well-written guide page

## Typography Rules

- Headings: line-height 1.1–1.2, letter-spacing -0.02em to -0.04em for display sizes
- Body: line-height 1.5–1.6
- Do not use the generic `h1=48px h2=36px h3=24px h4=20px` staircase — design a ratio with personality
- One display font with character + one functional body font = a design identity
- Weight contrast matters more than size contrast for hierarchy
- Use size JUMPS not gradual steps: display (64px) → h1 (36px) is better than 48 → 36 → 24 → 20
- Text color should vary by 2 levels max on the same surface: heading (dark) + body (medium). Three+ text shades on one surface = muddy.

## Color Rules

- Tint all grays — no neutral gray. Add warm hue for organic contexts, cool hue for technical contexts.
- Choose accent color based on emotional intent: warmth (amber, terracotta), confidence (deep blue-green), energy (electric yellow-green), authority (near-black with one bold accent)
- Never choose a color because it "looks premium" — choose it because it communicates something specific about this product
- Color hierarchy: 60% surface color, 30% text/border, 10% accent. Inverted hierarchy = confused interface.
- Test: put 5 screenshots of your design side-by-side with 5 random AI-generated pages. If they blend in, the palette is wrong.

## Dark Mode Rules

Dark mode is NOT "invert light mode":
- Use `#121212` to `#1A1A1A` range for backgrounds — never pure `#000000` (too harsh)
- Reduce saturation on dark surfaces (boosting saturation is the most common dark mode mistake)
- Replace shadows with surface-color elevation (shadows are invisible on dark surfaces)
- Increase border opacity for dark surfaces (light borders that worked on white become invisible)
- Adjust text contrast: dark mode often needs slightly lighter body text than light mode

## Spacing Rules

- Spacing must create RHYTHM, not repetition. `24px → 40px → 16px → 64px` has rhythm. `24px → 24px → 24px` is filler.
- Tight spacing = dense, information-rich. Generous spacing = editorial, premium. Pick one and commit.
- Padding should vary by section importance: hero gets more breathing room than a settings panel.
- Component internal padding should be proportional to component size: small button (8px 16px), large card (24px 32px).

## Animation Anti-Patterns

| Anti-pattern | Why it's banned | What to do instead |
|-------------|----------------|-------------------|
| Staggered entrance on list items (every item fades in 50ms apart) | THE most identifiable AI animation | Animate the container, not individual items. Or use a single scroll-reveal for the group |
| `hover: scale(1.05)` on every interactive element | Identical hover = template | Match hover intensity to element importance: subtle for nav, pronounced for primary CTA |
| `transition: all 0.3s ease` everywhere | Lazy default | Transition only the property that changes, with a project-specific easing curve |
| Parallax on every scroll section | Performance killer + AI tell | Reserve for ONE section maximum, or skip entirely |
| Skeleton loading on everything | Inverse of "spinner only" — equally generic | Match loading indicator to content type: skeleton for structured data, progress bar for operations, spinner for quick loads |
| `fadeIn` keyframe on page load | Every AI page fades in | Use `DOMContentLoaded` for instant render. Animate only user-triggered changes |
| Stat counter animation (0 → X) | Cheap "dynamic" illusion, universal AI tell | Show the number statically. If emphasis is needed, one subtle fade-in on scroll is acceptable |

## Iconography Rules

- Defaulting to outline-style icons (Feather, Lucide, Phosphor) with no weight customization is the AI icon tell. Customize stroke weight to match your type weight.
- Icon + text pair on every nav item, every card title, every section heading = decoration, not communication. Use icons where they add clarity, not everywhere.
- Same icon size everywhere is a template signal. Scale icons by importance: primary actions 24px, inline helpers 16px.
- Pick ONE icon family and commit. Mixing Lucide + Heroicons + custom = visual noise.

## Illustration Rules

- Abstract geometric illustrations (overlapping circles, gradient blobs, isometric shapes) are the AI illustration tell. If you use illustrations, they must be product-specific.
- People illustrations that look like Notion/Stripe clones (rounded features, muted palette) read as stock. Commission or generate product-specific illustration style.
- If the product has no illustration budget, use NO illustrations rather than AI-generated ones. Typography and whitespace carry more personality than generic illustrations.

## Component Anti-Patterns

- **Button with only color change on hover**: Add a physical state change — shadow shift, scale(1.02), border appearance
- **Cards with identical height**: Let content determine height. Equal height = template.
- **Navigation with underline on active**: Try background highlight, weight change, or color shift instead
- **Forms with labels above every field**: Consider inline labels for short forms, floating labels for complex ones
- **Modal with centered text**: Left-align modal content. Center-align only for single-CTA confirmations.
- **Toasts in the bottom-right corner only**: Consider top-center for success, bottom-right for background operations
- **Loading state = spinner only**: Show skeleton of the actual content shape, or progress bar with status text
- **Empty state = icon + "No data"**: Write what the user should do, why it matters, and give a CTA

## Responsive Anti-Patterns

- Identical font sizes on mobile (display type must scale down)
- Full-width everything on mobile (some elements benefit from constrained width even on small screens)
- Desktop padding preserved on mobile (tighten spacing proportionally)
- Multi-column tables not converted to card views on mobile
- Touch targets under 44px height
- Desktop hover-only interactions not adapted for touch

## Microcopy Rules

These surfaces are personality injection points — they MUST have written copy, not placeholder text:

| Surface | Bad (AI default) | Good (has character) |
|---------|-----------------|---------------------|
| Empty state | "No items found" | Write what the user should do next, with a reason to care |
| Error message | "Something went wrong" | Specific about what happened + what to do |
| Loading state | Spinner only | Brief text describing what's being fetched or computed |
| Success confirmation | "Saved" | Acknowledge what the user accomplished |
| Onboarding step | "Complete your profile" | Build anticipation: why does this step matter? |
| Button label | "Submit" | Describe the outcome: "Publish", "Send invitation", "Start trial" |
| 404 page | "Page not found" | Match product personality: guide the user somewhere useful |
| Tooltip | Repetition of label | Provide information the label doesn't contain |

## The Emoji Rule

Zero emoji anywhere in design documents or UI copy unless the product brief explicitly calls for it. Emoji in UI text is the single strongest signal of AI-generated content.

## Mechanical Quality Checks

Instead of subjective "does this look generic?" judgments, verify these concrete metrics:

- Count unique layout widths across sections. If all sections use the same max-width and padding → fail (no rhythm)
- Count distinct border-radius values. If fewer than 3 distinct values → fail (template radius)
- List all colors used. If all non-neutral colors belong to a single hue family (within 30 degrees on the color wheel) and map to a single Tailwind color scale (e.g., all blue-XXX or all slate-XXX) → fail (AI palette)
- Check all text/background pairs with a contrast checker. Any pair below 4.5:1 → fail (accessibility)
- Count font sizes. If more than 7 distinct sizes → fail (scale needs discipline). If fewer than 4 → fail (no hierarchy)
- Verify spacing values: if 3+ consecutive sections have identical top+bottom padding → fail (no rhythm)

## The Sniff Test

Before finalizing any design or implementation:

> "Could this design be for any other product?"

If the answer is "yes" or "maybe" — it is not done. Make it specific.

## The Three-Screenshot Test

Take screenshots of three different pages in your design. Cover the logo and product name. Can you still tell it's YOUR product? If not, the design lacks personality. Add domain-specific visual language until it's unmistakable.
