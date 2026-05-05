---
name: Web Search (Tavily)
version: "1.0.0"
description: Use when the user asks to search the web, look up current information, find recent news, compare products/libraries, or research any topic that requires up-to-date online data. Always prefer this over the built-in WebSearch tool.
---

# Web Search via Tavily

Use Tavily for all web search operations instead of the built-in WebSearch tool. Tavily returns higher-quality, structured results with content extraction.

## IRON LAW

**Always use Tavily CLI for web searches. Never use the built-in WebSearch tool.**

## When to Use

- User asks to search the web, look something up, or find current information
- Need up-to-date data not in training (news, prices, versions, status pages)
- Researching libraries, frameworks, or tools for comparison
- Finding documentation or answers for unfamiliar technologies
- Any task that requires real-time internet information

## Usage

### Basic Search

```bash
# Standard search
python ~/bin/tavily "search query"

# Limit results
python ~/bin/tavily "search query" -n 3

# News search
python ~/bin/tavily "search query" --topic news --days 7

# Raw JSON output (for programmatic use)
python ~/bin/tavily "search query" -j
```

### In Python (for scripts)

```python
from tavily import TavilyClient
import os

client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
results = client.search("query", max_results=5)

for r in results["results"]:
    print(r["title"])
    print(r["url"])
    print(r["content"])
```

### Search + Read (deep research)

For thorough research, combine search with content extraction:

```bash
# Search first
python ~/bin/tavily "topic" -n 5

# Then extract full content from promising URLs
python -c "
from tavily import TavilyClient
import os, json
client = TavilyClient(api_key=os.environ['TAVILY_API_KEY'])
result = client.extract(urls=['https://example.com'])
print(json.dumps(result, indent=2, ensure_ascii=False))
"
```

## Output Format

Each result includes:
- **title** — page title
- **url** — source URL
- **content** — relevant excerpt (may be truncated to 300 chars in CLI mode)

When presenting results to the user, always include source URLs as markdown links.

## Error Handling

- If `TAVILY_API_KEY` is not set, the CLI falls back to `~/.tavily` file
- If both are missing, instruct the user to configure the key (see installation guide)
- If search returns no results, try broader or rephrased queries
- Rate limits: the free tier allows ~1000 searches/month

## Comparison with Built-in WebSearch

| Aspect | Tavily | Built-in WebSearch |
|--------|--------|--------------------|
| Result quality | High (AI-optimized extraction) | Variable |
| Content depth | Full excerpts | Snippets |
| News support | `--topic news` | Limited |
| URL extraction | Built-in `extract()` | No |
| Structured output | JSON with clean schema | Variable |
| Citation support | URL + title pairs | URL only |

## Examples

```
User: "What's the latest version of React?"
→ python ~/bin/tavily "React latest version 2026" -n 3

User: "Compare Next.js vs Nuxt"
→ python ~/bin/tavily "Next.js vs Nuxt comparison 2026" -n 5

User: "Find recent news about Rust"
→ python ~/bin/tavily "Rust programming news" --topic news --days 7
```
