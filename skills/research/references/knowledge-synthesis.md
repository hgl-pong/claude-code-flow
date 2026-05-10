# Knowledge Synthesis

Merge multiple search results into a single, deduplicated, well-attributed answer. Never list source-by-source. Synthesize.

## Deduplication

### Merge Signals (same information)
- Identical or near-identical text
- Same author or organization
- Close timestamps on same topic
- Same entity references (names, URLs, IDs)

### Priority Order
1. Most complete (covers more detail)
2. Most authoritative (official > secondary > informal)
3. Most recent (when currency matters)

### Do NOT Deduplicate
- Different conclusions on the same topic
- Different viewpoints or perspectives
- Information that evolved over time (show progression)

## Citation Format

Inline: `[Source Type: description](location)`

Source list at end:
```markdown
## Sources
| Source | Type | Date | Authority |
|--------|------|------|-----------|
| Official docs | Documentation | 2024-12 | Highest |
| GitHub issue | Community | 2024-11 | High |
```

## Confidence Levels

### Freshness
| Age | Confidence |
|-----|------------|
| Today | High |
| This week | Good |
| This month | Moderate |
| Older | Lower — flag staleness |

### Authority
| Source Type | Authority |
|-------------|-----------|
| Official docs, spec, RFC | Highest |
| Maintainer/author response | High |
| Established blog, book | Good |
| Chat mid-thread, forum | Lower |

### Expressing Confidence
- **High**: "X is the case [2 authoritative sources, current]"
- **Moderate**: "X appears to be the case [1 source, corroborated indirectly]"
- **Low**: "X may be the case [single source, unverified]"

### Conflict Handling
1. Surface the disagreement explicitly
2. Present each position with its source
3. State which is more authoritative or recent
4. Do NOT silently pick one

## Summarization by Volume

| Size | Strategy |
|------|----------|
| Small (1-5) | Present all, merge where redundant |
| Medium (5-15) | Group by theme, highlight key findings |
| Large (15+) | High-level synthesis, offer drill-down |

## Anti-Patterns

- Listing source-by-source instead of synthesizing
- Including irrelevant keyword matches
- Burying the answer under methodology
- Omitting attribution for factual claims

## Workflow

```
Raw Results → Deduplicate → Cluster → Rank → Assess Confidence → Synthesize → Format
```

## Tips

- Start from the question, not the sources. Synthesis answers a question.
- When confidence is low, say so. Unclear attribution beats false certainty.
- Prefer fewer high-confidence claims over many low-confidence ones.
