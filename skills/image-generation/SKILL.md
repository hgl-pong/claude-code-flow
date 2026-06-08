---
name: image-generation
description: Use when the user wants to generate, draw, render, create, or edit images; delegates focused image work to artist subagents and supports bounded parallel batches
---

# Image Generation

Generate/edit images via dedicated artist subagents; coordinator does not do ad hoc image work.

## Use When

User asks to generate/draw/render/create/make images, icons, illustrations, concept art, diagrams, posters, mockups, sprites, visual assets; edit/vary existing images with refs/masks; or produce multiple independent image briefs.

Do not use for screenshot/chart analysis; use vision/OCR/diagram tools.

## Inputs

Infer defaults unless missing detail fundamentally changes output: prompt/brief, count, aspect/size, quality (`draft`/`normal`/`final`), output path, refs/masks, named provider/tool.

## Dispatch

Use `skills/workflow-driven-development/artist-prompt.md`.

One image/tightly coupled set → one artist. Independent batch → split jobs, dispatch concurrently with bounded concurrency for rate/quota/cost, don't parallelize dependent jobs, merge manifests.

## Provider

Use `scripts/generate-image.py` (9Router, hardcoded `cx/gpt-5.5-image`):

```bash
python scripts/generate-image.py --prompt "watercolor mountains at sunrise" --output out.png
```

Requires `NINEROUTER_URL` + `NINEROUTER_KEY`. Missing env → exit 2; artist returns `BLOCKED`. Script creates dirs, saves image, prints JSON manifest.

## Artist Output

Return status (`DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, `BLOCKED`), output paths, manifest (prompt/provider/model/params/refs/masks/failures/retries), and concerns (partial success, rejection, rate limit, quality).

## Completion

Summarize generated paths. Separate blocked/failed jobs. Never describe missing files as generated.
