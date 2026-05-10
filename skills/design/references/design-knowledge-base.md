# Design Knowledge Base

Reference these products for specific techniques — always state what you borrow AND what you deliberately break away from. Copy without divergence = template.

---

## Linear — Precision density, not minimalism

**Visual language**: Near-black surfaces, 4px grid discipline, hierarchy through weight not color, zero decorative elements.

**Concrete values**:
- Background: `#08090A` (canvas), `#0A0A0F` (surfaces)
- Text: `#FFFFFF` (headings), `#8B8D98` (body), `#565B66` (muted)
- Accent: `#5E6AD2` (their indigo — do NOT copy this exact shade)
- Font: Inter at 13px base size, `-0.01em` tracking on body
- Spacing: 4px grid — all values are multiples of 4
- Border-radius: 6px (everything), 8px (modals)
- Density: Table rows 36px height, list items 32px

**What to steal**: The density philosophy — every pixel earns its place. Information density without visual clutter. How to use type weight (400/500/600) as the primary hierarchy tool instead of color or size.

**What to avoid copying**: Inter font (too common in dev tools), indigo accent (now generic for dev tools), their exact gray palette.

**Best for**: Developer tools, SaaS dashboards, data-heavy interfaces.

**Divergence prompt**: If your product isn't a developer tool, borrow the density discipline but warm the palette and increase the base type size to 14-15px.

---

## Vercel — Typographic confidence

**Visual language**: Monochrome palette forces typography to carry all meaning. Uppercase micro-labels. Generous whitespace as a statement.

**Concrete values**:
- Background: `#000000` (hero), `#FFFFFF` (content sections)
- Text: `#000000` / `#FFFFFF` (headings), `#666666` (body), `#888888` (muted)
- Accent: None in palette — accent comes from content (gradients on cards, colored terminal text)
- Font: Geist (their custom font — use Geist Mono as alternative), tight tracking
- Headlines: 60-80px, weight 700, line-height 1.0
- Spacing: 128px between major sections, 64px between minor
- Border-radius: 8px (cards), 4px (code blocks)

**What to steal**: "Nothing is decoration" discipline — if it's not content, remove it. How monochrome + typography alone creates hierarchy. The confidence to use pure black and white.

**What to avoid copying**: Pure `#000`/`#fff` (cold without warmth), Geist (their brand font, use similar geometric sans instead).

**Best for**: Documentation, infrastructure, developer-facing products.

**Divergence prompt**: If your product needs warmth, start from Vercel's structure but add one warm accent color and use off-whites instead of pure white.

---

## Stripe — Editorial asymmetry

**Visual language**: Asymmetric hero compositions, light font weights for display text, editorial section rhythm with distinct visual treatments per section.

**Concrete values**:
- Background: `#F6F9FC` (canvas), `#FFFFFF` (cards)
- Accent: `#635BFF` (their purple — do NOT copy)
- Font: `Inter + system-serif` for accent (their pairing)
- Hero: Asymmetric split, illustration on one side, text on other
- Section spacing: 80-120px between sections with distinct visual treatments
- Cards: `8px` radius, subtle shadow `0 2px 4px rgba(0,0,0,0.05)`
- Animation: Elements animate in sequentially, not all at once

**What to steal**: Sections that feel visually distinct from each other. The editorial approach — each section has its own visual treatment. Asymmetric composition as a design tool.

**What to avoid copying**: `#635BFF` purple (now everyone's "premium" color), gradient hero backgrounds (overdone).

**Best for**: Trust-critical interfaces, payment flows, landing pages.

**Divergence prompt**: If your product isn't financial, borrow the editorial section rhythm but use warmer colors and less "corporate" typography.

---

## Notion — Content-first spacing

**Visual language**: Warm off-white surfaces, serif + sans pairing where the font mix IS the brand. Layout feels like a physical medium.

**Concrete values**:
- Background: `#FFFFFF` (canvas), `#F7F6F3` (sidebar)
- Text: `#37352F` (headings), `#9B9A97` (muted)
- Accent: `#2383E2` (their blue — contextual, not everywhere)
- Font: System serif for headings (ie. "Noto Serif SC"), system sans for body
- Spacing: Generous — 40px between blocks, 64px between sections
- Border-radius: 4px (most elements), no rounded cards
- Width: Content max-width ~708px (reading-optimized)

**What to steal**: Layout that feels like paper/physical medium. Warm off-whites. The idea that content IS the design — minimal chrome. Serif + sans as a brand signal.

**What to avoid copying**: Their exact neutral palette (looks like Notion clone), the loose density (only fits content tools).

**Best for**: Knowledge tools, writing interfaces, educational products.

**Divergence prompt**: If your product is not content-focused, borrow the warmth but increase information density.

---

## Apple — Extreme scale contrast

**Visual language**: Massive display type paired with tiny captions. Scale ratio IS the design. Full-bleed photography as primary color.

**Concrete values**:
- Background: `#FFFFFF` / `#000000` (bipolar, section-dependent)
- Headlines: 80-96px on desktop, SF Pro Display weight 600-700
- Captions: 12-14px, SF Pro Text weight 400, uppercase tracking 0.08em
- Scale ratio: ~1.5x between heading levels (extreme)
- Section spacing: 120-160px between sections (extreme generosity)
- Border-radius: 12-20px (cards), 8px (buttons)
- Animation: Scroll-triggered reveals, one element at a time

**What to steal**: Treating scale difference as the main design tool (not color, not gradients). The courage to leave massive whitespace. Full-bleed visuals as section dividers.

**What to avoid copying**: Centered composition (overused), SF Pro (system font, no differentiation), pure black/white without warmth.

**Best for**: Consumer showcase, premium product pages, high-stakes first impressions.

**Divergence prompt**: If your product is not a showcase, borrow the scale contrast principle but reduce the extremes — 48px display instead of 96px, 32px spacing instead of 160px.

---

## Craft Docs — Warmth through imperfection

**Visual language**: Slightly rounded but not bubbly. Warm grays with red undertones. Micro-animations with spring physics. "Handmade but precise" tension.

**Concrete values**:
- Background: `#F5F1EB` (warm canvas), `#FFFFFF` (cards)
- Text: `#2C2C2E` (headings), `#8E8E93` (muted)
- Accent: `#E74C3C` (warm red) or `#FF6B35` (orange)
- Font: System font with serif accents
- Border-radius: 12px (cards), 8px (buttons), 16px (modals)
- Shadow: `0 4px 12px rgba(0,0,0,0.08)` — warm, soft
- Spacing: 8px base, generous use of space between elements

**What to steal**: The "handmade but precise" tension — careful layouts that feel touched by a human. Warm grays with color undertones. Spring physics for micro-animations.

**What to avoid copying**: Their specific off-white (context-dependent).

**Best for**: Productivity tools, creative apps, consumer-leaning SaaS.

---

## Raycast — Speed as a design principle

**Visual language**: Keyboard-first visual language. Monospace + geometric sans pairing. Color as semantic signal, not decoration. Dark-first palette with precise opacity.

**Concrete values**:
- Background: `#191A1D` (canvas), `#2B2D30` (surfaces)
- Text: `#ECEFF4` (headings), `#9CA0A8` (body), `#6B7080` (muted)
- Accent: `#FF6363` (their coral — semantic: destructive/warning only)
- Font: System sans + monospace for keyboard shortcuts and data
- Density: Extremely high — items 36-40px, compact sidebar
- Border-radius: 8px (cards), 6px (list items), 12px (modals)
- Opacity layers: Surfaces at 60%, 80%, 100% to create depth without shadows

**What to steal**: Designing for power users without alienating new users. Color as semantic signal (not decorative). How to pack density without visual noise.

**What to avoid copying**: Their specific coral accent, dark-only palette.

**Best for**: Productivity tools, command interfaces, developer utilities.

---

## Figma — Layered density with confident color

**Visual language**: Bold accent color used purposefully. Toolbars that pack information without feeling cramped. Contextual panels that adapt to selection.

**Concrete values**:
- Background: `#1E1E1E` (canvas), `#2C2C2C` (panels)
- Accent: `#7B61FF` (their purple — on interactive ONLY, never decorative)
- Font: Inter at 11-12px base (extreme density)
- Toolbar height: 40px, panel width: 240px
- Border-radius: 6px (consistent)
- Spacing: 4px internal, 8px between groups

**What to steal**: Density and clarity are not oppositives. How to use ONE accent color with surgical precision (only interactive elements, never backgrounds or decoration).

**What to avoid copying**: Their exact purple, the canvas-centric layout.

**Best for**: Creative tools, canvas interfaces, complex SaaS with many states.

---

## Loom — Personality in empty states

**Visual language**: Empty states that tell a story. Loading states with brand voice. Onboarding that celebrates the user.

**Concrete values**:
- Background: `#FFFFFF` (canvas), `#F5F5F0` (secondary)
- Accent: `#625DF5` (their purple) + `#FF5B54` (their coral for emphasis)
- Font: Circular (their brand font), 16px base
- Empty states: Custom illustration + personality headline + actionable CTA
- Onboarding: Step-by-step with celebration moments
- Border-radius: 12px (cards), 8px (buttons)

**What to steal**: Writing microcopy before designing the surrounding layout. Empty states as brand moments, not afterthoughts. Onboarding that builds anticipation.

**What to avoid copying**: The video-centric color system.

**Best for**: Any app where user activation matters, onboarding flows.

---

## Are.na — Deliberate anti-polish

**Visual language**: Grid density that respects content over decoration. Restraint as aesthetic choice. Typography that steps back and lets content speak.

**Concrete values**:
- Background: `#FFFFFF` (canvas), `#1714` (their green as accent)
- Font: System serif for everything
- Spacing: Minimal — content fills the space
- Border-radius: 2-3px (barely rounded)
- No shadows, no gradients, no decorative elements

**What to steal**: The courage to look "undesigned" because the content IS the design. Extreme restraint as a deliberate choice.

**What to avoid copying**: The minimal chrome (requires strong content to support it).

**Best for**: Content curation, creative tools, portfolio/showcase interfaces.

---

## Extended Reference Library

For 69+ additional real-world DESIGN.md examples covering every domain (AI tools, fintech, automotive, media, SaaS), see:
- **Repository**: https://github.com/VoltAgent/awesome-design-md
- **Browse online**: https://getdesign.md
- Each file follows the Google Stitch 9-section format with concrete token values
