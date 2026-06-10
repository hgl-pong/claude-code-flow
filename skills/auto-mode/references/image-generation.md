# Image Generation Capability

Use when auto-mode needs to create, generate, draw, render, edit, or vary images, pictures, icons, illustrations, diagrams, mockups, sprites, posters, or other visual assets.

This is folded from 9Router image generation guidance. The model is fixed: `cx/gpt-5.5-image` (GPT 5.5 image).

Do not use for screenshot/chart analysis; use vision/OCR/diagram inspection instead.

## Endpoint

Default endpoint is fixed:

```text
http://localhost:20128/v1/images/generations
```

`POST /v1/images/generations?response_format=binary` returns raw image bytes for direct file saves.

Optional env:

- `NINEROUTER_URL` overrides the base URL or full endpoint when needed.
- `NINEROUTER_KEY` sets `Authorization: Bearer <key>` only when the local proxy requires auth.
- By default, no auth header is sent.

## Request

Common fields:

| Field | Required | Notes |
|---|---|---|
| `model` | yes | always `cx/gpt-5.5-image` |
| `prompt` | yes | image description |
| `n` | no | count; provider-dependent |
| `size` | no | e.g. `1024x1024`, `1792x1024` |
| `quality` | no | use `high` for final, lower for drafts |

Use `scripts/generate-image.py` exclusively:

```bash
python scripts/generate-image.py --prompt "watercolor mountains at sunrise" --output out.png
```

The script calls:

```text
http://localhost:20128/v1/images/generations?response_format=binary
```

with JSON body including `model`, `prompt`, `size`, `quality`, and `n`.

## Dispatch

Coordinator does not do ad hoc image work. One image or tightly-coupled set → one artist task. Independent batch → split jobs and run bounded parallel artists. Do not parallelize dependent variants.

Inputs to infer unless missing detail fundamentally changes output: brief, count, aspect/size, quality (`draft`/`normal`/`final`), output path, refs/masks.

## Prompt Work

Preserve the user's subject, style, constraints, text, brand, and references. Use concrete visual language: medium, composition, lighting, materials, texture, camera/view, layout. For text-heavy images, dense diagrams, labels, or multi-panel layouts, prefer high quality. For drafts/sweeps, prefer lower quality unless told otherwise.

For edits, preserve requested invariants and use provided reference images or masks.

## Output

Default path if unspecified:

```text
.claude/deliverables/<task-name>/images/
```

Use stable descriptive filenames. For multiples, suffix `-01`, `-02`, etc.

Return status (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, `BLOCKED`), output paths, manifest, and concerns. Manifest should include prompts, provider/tool, model, size/aspect, quality, count, refs/masks, failed jobs, provider errors, rate-limit or quality concerns, and retry recommendations.

Never describe missing files as generated.
