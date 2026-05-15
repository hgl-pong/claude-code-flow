# Connectors

External tools available to skills via MCP servers. Skills reference these with `~~category` placeholders.

| Category | Placeholder | Tool |
|----------|------------|------|
| Code intelligence | `~~code-intel` | GitNexus (query, context, impact, rename) |
| Figma | `~~figma` | Figma MCP server (`use_figma`, file/design context tools) |
| Image generation | `~~image-gen` | img-cli (`img generate`, `img describe`) |
| Browser automation | `~~browser` | Playwright MCP (`@playwright/mcp`) — navigate, screenshot, click, type, assert |
| Output processing | `~~context-mode` | context-mode (ctx_execute, ctx_batch_execute, ctx_search) |
| WeChat dev | `~~weapp-dev` | WeChat DevTools (miniprogram-automator) |

## How to Use in Skills

```markdown
If **~~code-intel** is connected:
- Run `gitnexus_impact` to check blast radius before changes
- Use `gitnexus_query` to find execution flows
```
