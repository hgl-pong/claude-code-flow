# Connectors

External tools available to skills via MCP servers. Skills reference these with `~~category` placeholders.

| Category | Placeholder | Tool |
|----------|------------|------|
| Browser automation | `~~browser` | Playwright MCP (`@playwright/mcp`) — navigate, screenshot, click, type, assert |
| Output processing | `~~context-mode` | context-mode (ctx_execute, ctx_batch_execute, ctx_search) |
| WeChat dev | `~~weapp-dev` | WeChat DevTools (miniprogram-automator) |

## How to Use in Skills

```markdown
If **~~browser** is connected:
- Navigate to pages and verify UI changes
- Screenshot for visual regression
```
