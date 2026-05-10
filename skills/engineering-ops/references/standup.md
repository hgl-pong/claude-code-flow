# Standup Report

## Modes

### Auto-Pull

Pull activity from git and PR history. Use when you want a data-driven update.

If **~~code-intel** is connected: prefer `gitnexus_detect_changes` and `gitnexus_query` for richer codebase activity data (affected symbols, execution flows, impact analysis) over raw git commands.

```bash
git log --since="yesterday" --author="$(git config user.name)" --oneline --no-merges
git log --since="1 week ago" --author="$(git config user.name)" --format="%h %s" --no-merges
git diff --stat main...HEAD
```

Gather: commits, changed files, open PRs, review comments, merged PRs.

### Manual

User provides raw notes. You structure them into the template. Use when activity spans non-git work (meetings, design reviews, investigations).

## Output Template

```markdown
## Yesterday
- [ verb ] [ what ] -- [ outcome or status ]
- Fixed login timeout bug -- deployed to staging, verified
- Reviewed PR #142 (payment refactor) -- approved with comments
- Meeting: architecture review for search service

## Today
- [ ] [ planned work ]
- Continue payment integration tests
- Pair with @alice on caching strategy

## Blockers
- [ blocker ] -- [ what I need / who I'm waiting on ]
- Waiting on DB access from ops team -- requested Monday
- API spec for notifications not finalized -- @bob reviewing
```

### Formatting Rules

- Start every bullet with a verb: Fixed, Shipped, Reviewed, Started, Continued, Blocked
- One line per item -- no paragraphs
- Link PRs, issues, and tickets by number
- Mark completed items clearly
- Blockers must state the ask, not just the problem

## Customization

Adapt the output for the audience:

- **Team standup** -- Technical detail, link PRs and issues
- **Manager update** -- Progress toward milestones, blockers with dates
- **Slack message** -- Compressed format, emoji-compatible, under 10 lines

Specify which format when triggering the skill. Default is team standup.

## If Connectors Available

If **~~code-intel** is connected:
- Use `gitnexus_context` on recently changed symbols to summarize what each commit actually did (not just the commit message)
- Query open PRs and their review status to surface items for Today and Blockers sections

## Tips

- Run this skill every morning before standup. Consistency beats perfection.
- After generating, add context only you know -- upcoming meetings, decisions, conversations. The skill fills the git-shaped gaps; you fill the human-shaped ones.
- For async teams, paste the output into Slack/Teams. For sync standups, use it as speaker notes -- don't read it verbatim.
