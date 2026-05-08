# Anti-AI-Design Rules

AI-generated UI looks like every other AI-generated UI. These rules exist to prevent that.

Shared by: `designer` (design phase) and `forge` (implementation phase).

---

## Banned Elements — require explicit written justification to use

If you use any of these without justification, the output will be flagged as AI-generic:

| Element | Why it's banned | What to do instead |
|---------|----------------|-------------------|
| Blue-purple gradient hero/accent | Every AI design uses it | Pick a palette specific to this product's domain and tone |
| Glassmorphism / frosted-glass cards | Visual trend with no functional benefit | Use surface elevation through color difference, not blur |
| Gradient text on metrics or numbers | The AI "premium data" cliche | Bold weight + color contrast for emphasis |
| Identical card grid (Card > Image > Title > Description > CTA) | The template layout | Vary card sizes, break the grid, design for actual content |
| Bounce / elastic easing on more than one element | "Playful" default that reads as template | Custom cubic-bezier per interaction type |
| Fade-in-on-scroll on every section | Adds no meaning, reads as filler animation | Reserve scroll-triggered animation for one intentional moment |
| Cards nested inside cards | Structural laziness | Use whitespace, borders, or typographic hierarchy instead |
| Inter + Roboto + system-sans with zero customization | The AI font stack | Pick one font with character; pair it deliberately |
| Pure `#9ca3af` / `#6b7280` (Tailwind gray-400/500) | Neutral gray is a reset to template | Tint all grays: add 4-8% warm or cool hue |
| Shadow on every card/container | "Elevated" default | Use either shadow or border, not both, not everywhere |
| `rounded-xl` on everything | One-size radius is a template signal | Vary radii: inputs differ from cards, cards differ from modals |
| Five "equal" brand colors | No visual hierarchy | One dominant surface, one sharp accent, rest are neutrals |
| `primary` / `accent-500` / `secondary` token names | Generic naming = generic thinking | Semantic names: `surface-canvas`, `text-heading`, `interaction-focus` |

## Layout Anti-Patterns

These are structural tells that a layout was generated, not designed:

- **Hero → Features Grid → CTA → Footer** (the AI template sequence — break the order)
- **Every section centered and symmetric** (asymmetry signals intentionality)
- **Identical padding on all sections** (`64px → 64px → 64px` is repetition, not rhythm)
- **All headings the same visual weight** (scale contrast IS design — vary it)
- **Sections that could be swapped in any order** (each section should earn its position)

## Typography Rules

- Headings: line-height 1.1–1.2, letter-spacing -0.02em to -0.04em for display sizes
- Body: line-height 1.5–1.6
- Do not use the generic `h1=48px h2=36px h3=24px h4=20px` staircase — design a ratio with personality
- One display font with character + one functional body font = a design identity
- Weight contrast matters more than size contrast for hierarchy

## Color Rules

- Tint all grays — no neutral gray. Add warm hue for organic contexts, cool hue for technical contexts.
- Choose accent color based on emotional intent: warmth (amber, terracotta), confidence (deep blue-green), energy (electric yellow-green), authority (near-black with one bold accent)
- Never choose a color because it "looks premium" — choose it because it communicates something specific about this product

## Microcopy Rules

These surfaces are personality injection points — they MUST have written copy, not placeholder text:

| Surface | Bad (AI default) | Good (has character) |
|---------|-----------------|---------------------|
| Empty state | "No items found" | Write what the user should do next, with a reason to care |
| Error message | "Something went wrong" | Specific about what happened + what to do |
| Loading state | Spinner only | Brief text describing what's being fetched or computed |
| Success confirmation | "Saved" | Acknowledge what the user accomplished |
| Onboarding step | "Complete your profile" | Build anticipation: why does this step matter? |

## The Emoji Rule

Zero emoji anywhere in design documents or UI copy unless the product brief explicitly calls for it. Emoji in UI text is the single strongest signal of AI-generated content.

## The Sniff Test

Before finalizing any design or implementation:

> "Could this design be for any other product?"

If the answer is "yes" or "maybe" — it is not done. Make it specific.
