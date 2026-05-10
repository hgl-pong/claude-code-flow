# Layout Patterns

Concrete layout composition patterns organized by screen type. Use these as starting points — never copy verbatim without adapting to the product's content and personality.

---

## Page-Level Composition

### Landing / Marketing Page

```
┌──────────────────────────────────────────────┐
│ Nav: logo left, links center, CTA right      │
├──────────────────────────────────────────────┤
│                                              │
│  Asymmetric Hero                             │
│  ┌──────────┐  ┌──────────────────────┐     │
│  │ Headline  │  │ Visual (screenshot,  │     │
│  │ Subtitle  │  │ illustration, or     │     │
│  │ CTA       │  │ product image)       │     │
│  └──────────┘  └──────────────────────┘     │
│  60/40 or 55/45 split, NEVER 50/50          │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  Social proof strip                          │
│  Logo row with opacity treatment             │
│  Tight vertical spacing (24-32px)            │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  Feature section — EDITORIAL layout          │
│  ┌────────────────────┐ ┌────────┐          │
│  │ Headline + body    │ │ Image  │          │
│  │ (60% width)        │ │ (40%)  │          │
│  └────────────────────┘ └────────┘          │
│                                              │
│  NEXT feature: FLIP the split                │
│  ┌────────┐ ┌────────────────────┐          │
│  │ Image  │ │ Headline + body    │          │
│  │ (40%)  │ │ (60% width)        │          │
│  └────────┘ └────────────────────┘          │
│                                              │
│  Alternating direction = visual rhythm       │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  CTA section — BREAK the pattern             │
│  Full-bleed background color change          │
│  Centered OR asymmetric, but different       │
│  from everything above                       │
│                                              │
├──────────────────────────────────────────────┤
│ Footer                                       │
└──────────────────────────────────────────────┘
```

**Key rules**:
- Hero split must be asymmetric (60/40 or 55/45, never 50/50)
- Feature sections alternate direction (image-left, image-right)
- One section breaks the pattern entirely (different bg, different layout, different density)
- Spacing varies between sections: hero (96px) → social proof (48px) → features (80px) → CTA (64px)

### Dashboard

```
┌────────┬─────────────────────────────────────┐
│        │ Top bar: search, notifications, user │
│        ├───────┬───────┬───────┬─────────────┤
│  Side  │ KPI 1 │ KPI 2 │ KPI 3 │ KPI 4      │
│  Nav   │ card  │ card  │ card  │ card        │
│        ├───────┴───────┴───────┴─────────────┤
│        │                                      │
│        │ Primary content area                 │
│        │ (chart, table, or list)              │
│        │                                      │
│        ├──────────────────┬───────────────────┤
│        │                  │                   │
│        │ Secondary data   │ Sidebar panel     │
│        │ (60-70%)         │ (30-40%)          │
│        │                  │                   │
│        └──────────────────┴───────────────────┘
└────────┴─────────────────────────────────────┘
```

**Key rules**:
- Side nav: icon-only collapsed (56-64px) or expanded with labels (200-240px)
- KPI cards: compact (64-80px height), value + label + trend indicator
- Primary content gets 60-70% of width, secondary 30-40%
- Content density = high. Padding is 12-16px, not 24-32px.

### Settings / Form Page

```
┌──────────────────────────────────────────────┐
│ Page title + description (generous top space) │
├──────────────────────────────────────────────┤
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ Section card: "Profile"                │  │
│  │ ┌──────────────────────────────────┐   │  │
│  │ │ Label    Input field             │   │  │
│  │ │ Label    Input field             │   │  │
│  │ │ Label    Input field   [Action]  │   │  │
│  │ └──────────────────────────────────┘   │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ Section card: "Notifications"          │  │
│  │ Toggle rows with description           │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ Danger zone: distinct border color     │  │
│  │ Destructive action with confirmation   │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  Footer actions: Cancel (ghost) + Save (primary) │
└──────────────────────────────────────────────┘
```

**Key rules**:
- Max form width: 600-720px (never full-width forms)
- Section cards with clear titles, not one giant form
- Danger zone separated visually (red-tinted border or background)
- Footer actions: secondary left-aligned, primary right-aligned

### Data Table / List

```
┌──────────────────────────────────────────────┐
│ Title + description │ Search │ Filter │ + Add │
├──────────────────────────────────────────────┤
│ Bulk actions bar (appears when items selected)│
├──────────────────────────────────────────────┤
│ ┌────┬──────────┬────────┬──────┬───────┐   │
│ │ □  │ Name     │ Status │ Date │ Actions│   │
│ ├────┼──────────┼────────┼──────┼───────┤   │
│ │ □  │ Item 1   │ badge  │ ...  │ ⋯     │   │
│ │ □  │ Item 2   │ badge  │ ...  │ ⋯     │   │
│ │ □  │ Item 3   │ badge  │ ...  │ ⋯     │   │
│ └────┴──────────┴────────┴──────┴───────┘   │
├──────────────────────────────────────────────┤
│ Showing 1-25 of 342  │  < 1 2 3 ... 14 >   │
└──────────────────────────────────────────────┘
```

**Key rules**:
- Row height: 48-56px (compact) or 64-72px (comfortable)
- Sticky header when table scrolls
- Pagination below, showing range + total
- Empty state replaces table body, not just "no rows"

### Authentication (Login / Signup)

```
┌──────────────────────────────────────────────┐
│                    │                          │
│                    │                          │
│   Brand visual     │   ┌──────────────────┐  │
│   or illustration  │   │ Logo             │  │
│   (50-60% width)   │   │ Headline         │  │
│                    │   │                  │  │
│                    │   │ Email input      │  │
│                    │   │ Password input   │  │
│                    │   │ [Primary button] │  │
│                    │   │                  │  │
│                    │   │ Secondary link   │  │
│                    │   └──────────────────┘  │
│                    │   (40-50% width)         │
└──────────────────────────────────────────────┘
```

**Key rules**:
- Split layout: brand visual left, form right
- Form container: centered vertically, max-width 400px
- One primary action per screen
- Social login below primary button, with divider ("or continue with")
- Error states: inline below field, not alert boxes

### Chat / Messaging Interface

```
┌────────┬─────────────────────────────────────┐
│        │ Header: contact name, status, actions│
│  Side  ├─────────────────────────────────────┤
│  bar   │                                      │
│        │ Scrollable message thread            │
│ Conv   │ ┌──────────────────────┐            │
│ list   │ │ Received message     │            │
│        │ └──────────────────────┘            │
│        │        ┌──────────────────────┐     │
│        │        │ Sent message         │     │
│        │        └──────────────────────┘     │
│        │                                      │
│        ├─────────────────────────────────────┤
│        │ Composer: input + attachments + send │
│        │ (sticky bottom, not scrollable)      │
└────────┴─────────────────────────────────────┘
```

**Key rules**:
- Message alignment: received left, sent right (universal convention)
- Composer fixed to viewport bottom, thread scrolls above it
- New messages auto-scroll to bottom, with "new message" indicator if user scrolled up
- Sidebar: conversation list with preview text, active state, unread badge
- Thread should anchor to bottom (newest message visible), not top

### Kanban / Board View

```
┌──────────────────────────────────────────────┐
│ Board title │ Filter │ View toggle │ + Column │
├──────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│ │ Backlog  │ │ In Prog │ │ Done    │  ...   │
│ │ (count)  │ │ (count) │ │ (count) │        │
│ ├─────────┤ ├─────────┤ ├─────────┤        │
│ │ ┌─────┐ │ │ ┌─────┐ │ │ ┌─────┐ │        │
│ │ │Card │ │ │ │Card │ │ │ │Card │ │        │
│ │ └─────┘ │ │ └─────┘ │ │ └─────┘ │        │
│ │ ┌─────┐ │ │ ┌─────┐ │ │         │        │
│ │ │Card │ │ │ │Card │ │ │         │        │
│ │ └─────┘ │ │ └─────┘ │ │         │        │
│ │         │ │         │ │         │        │
│ └─────────┘ └─────────┘ └─────────┘        │
│  ← Horizontal scroll if overflow →          │
└──────────────────────────────────────────────┘
```

**Key rules**:
- Primary scroll axis: HORIZONTAL (columns), not vertical (page)
- Cards within columns: vertical scroll if column overflows
- Column width: fixed (260-320px) or flexible
- Card design: compact — title, assignee avatar, one metadata line
- Drag target: entire column is drop zone, card insertion point visualized

### Master-Detail (Email / Issue Tracker)

```
┌──────────────────────────────────────────────┐
│ Top bar: search, view controls               │
├──────────────┬───────────────────────────────┤
│              │                               │
│  List pane   │  Detail pane                  │
│  (30-40%)    │  (60-70%)                     │
│              │                               │
│  ┌────────┐  │  Title                        │
│  │ Item 1 │  │  Metadata row                 │
│  │ Item 2 │  │                               │
│  │ Item 3 │  │  Content area                 │
│  │ Item 4 │  │  (scrollable)                 │
│  │   ...  │  │                               │
│  └────────┘  │  Action bar (sticky bottom)   │
│              │                               │
├──────────────┴───────────────────────────────┤
│ Status bar (optional)                        │
└──────────────────────────────────────────────┘
```

**Key rules**:
- List pane: compact items (title + one metadata line), active item highlighted
- Detail pane: full content, scrollable independently from list
- Selecting an item in list updates detail pane WITHOUT page navigation
- Responsive: on mobile, list takes full width → tap opens detail as full screen (back button)

## Section Rhythm Patterns

Use these to create visual rhythm between sections:

### Pattern A: Alternating Density
```
Dense section (data, cards) →
  generous spacer (64-80px) →
Sparse section (headline + subtext only) →
  moderate spacer (40-48px) →
Dense section again
```

### Pattern B: Color Break
```
Surface-canvas section →
Surface-raised section (bg color change, no spacer needed) →
Surface-canvas section
```
Use when content is similar density. The color change creates the rhythm.

### Pattern C: Scale Contrast
```
Large-scale section (big type, big image, lots of space) →
Compact section (small type, tight spacing) →
Large-scale section
```
Best for marketing pages where sections need to feel distinct.

### Combining Patterns

Real pages combine patterns. Use these combinations as guides:

| Page type | Recommended combination |
|-----------|----------------------|
| Landing page | A + B + C rotated across sections |
| Dashboard | A only (density alternation between KPI row and chart) |
| Settings | B only (card boundaries create rhythm) |
| Data table | None (consistent density is correct for data) |
| Chat / Kanban | None (functional layout, not editorial) |
| Authentication | None (single-purpose functional layout) |
| Master-Detail | None (functional split-pane, not editorial) |

## Signature Moment Patterns

Every page needs ONE element that breaks the pattern:

| Pattern | How it works | Example |
|---------|-------------|---------|
| Oversized type | One headline at 80-120px, rest normal | Stripe's hero text |
| Full-bleed visual | Image or color that spans viewport width | Apple product pages |
| Asymmetric placement | Content offset to one side, not centered | Vercel case studies |
| Color block | One section in a bold, unexpected color | Notion's colored sections |
| Data visualization | Live chart or animated metric | Linear's issue graph |
| Illustration/3D | Custom visual element in an otherwise text page | Stripe headers |
| Typographic contrast | Extreme weight difference (900 vs 200) | Craft Docs |
| Scroll-triggered transform | Section that changes as you scroll (counter, morph, reveal) | Stripe's scrolling demos |
| Interactive demo | Embedded playground, sandbox, or live preview | Tailwind's playground |

## Responsive Collapse Strategy

When designing responsive behavior, specify for each section:

| Desktop behavior | Tablet collapse | Mobile collapse |
|-----------------|-----------------|-----------------|
| Side-by-side split | Stack, image below text | Full-width stacked |
| Multi-column grid | 2 columns | Single column |
| Side nav + content | Hamburger + full-width content | Bottom nav or hamburger |
| Table with many columns | Horizontal scroll or card view | Card list view |
| Hero 60/40 split | Stack: text then image | Stack: text then image, smaller image |
| Dashboard KPI row (4 col) | 2x2 grid | 2x2 or vertical stack |
| Auth split layout | Form only, brand visual hidden | Form only, full-width |
| Settings form (max 720px) | Same width, reduced card padding | Full-width, no card borders |
| Chat sidebar + thread | Sidebar collapses to drawer, thread full-width | Thread only, sidebar via back nav or drawer |
| Kanban columns (horizontal scroll) | 2 visible columns, rest scroll | Single column list view (stack columns) |
| Master-Detail (30/70 split) | Detail pane below list, or tab toggle | List full-width, detail as full-screen push (back button) |

### Table-to-Card Transformation

When a data table collapses to mobile cards:
- Primary field (usually "Name") becomes the card headline
- Status/date become subtitle metadata
- Actions move to card footer or context menu
- Bulk selection removed; individual card actions only
- Sort/filter moves to a sheet or top filter bar

**Mobile-specific rules**:
- Touch targets: minimum 44px height
- Form inputs: at least 48px height
- Bottom sheet > modal for mobile actions
- Sticky headers/CTAs: allowed, must not cover > 20% of viewport
