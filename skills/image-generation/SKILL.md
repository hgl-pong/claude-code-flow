---
name: image-generation
description: Use when the user wants to generate, draw, render, create, or edit images; delegates focused image work to artist subagents and supports bounded parallel batches
---

# Image Generation

Generate or edit images through a dedicated `artist` subagent instead of doing ad hoc image work in the coordinator.

## When to use

Use this skill when the user asks to:

- generate, draw, render, create, or make an image
- create icons, illustrations, concept art, diagrams, posters, mockups, sprites, or visual assets
- edit or vary an existing image with reference images or masks
- produce multiple independent images from a list of briefs

Do not use this for analyzing an existing screenshot or chart. Use the relevant vision/OCR/diagram tool instead.

## Inputs to collect or infer

For each image job, identify:

- prompt or creative brief
- number of images
- aspect ratio or size
- quality target: draft, normal, or final
- output directory or filename
- reference images and masks, if editing
- provider/tool preference, if the user named one

If a detail is unspecified, choose the simplest reasonable default. Ask only when the missing detail changes the result fundamentally.

## Dispatch model

Delegate generation to `skills/subagent-driven-development/artist-prompt.md`.

For one image or one tightly-coupled set, dispatch one artist subagent.

For many independent images:

1. Split the request into independent image jobs.
2. Dispatch artist subagents concurrently up to `CCF_MAX_PARALLEL_AGENTS`.
3. Use lower concurrency if the provider has known rate limits, quota limits, or high cost.
4. Do not parallelize jobs that depend on earlier generated images.
5. Merge the returned manifests into one final summary.

## Provider neutrality

Do not assume a provider. The artist should use whatever image path is explicitly available in the session, such as:

- 9Router-compatible image generation via `NINEROUTER_URL` and optional `NINEROUTER_KEY`
- GPT Image / OpenAI tooling via `OPENAI_API_KEY` or an installed `gpt-image` CLI
- a user-configured MCP image tool
- a local image service such as SDWebUI or ComfyUI, if the user configured it

If no image tool is configured, return `BLOCKED` with the exact missing configuration and one concise setup example. Do not pretend an image was generated.

## Artist output contract

Each artist subagent must return:

- status: `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`
- output paths for generated files
- a manifest containing prompt, tool/provider, model if known, params, refs/masks, failures, and retry notes
- concerns for partial success, provider rejection, rate limit, or quality limitations

## Completion

Summarize generated images by path. Include blocked or failed jobs separately. Never describe missing files as generated.
