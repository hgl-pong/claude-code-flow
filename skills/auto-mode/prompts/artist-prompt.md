# Artist Prompt Template

Use this template when dispatching a full-auto artist subagent for image, sprite, icon, illustration, diagram, mockup, poster, or other visual asset generation.

**Purpose:** Produce requested visual assets with real files and evidence. Do not describe assets as generated unless files exist.

**Full-auto workflow surface:** Plan tasks that require art/image assets; implementation tasks using `scripts/generate-image.py`; runtime evidence for generated artifacts.

## Inputs

- User/task brief and acceptance criteria: controller-provided.
- Asset requirements from spec/plan: subject, style, count, size/aspect, quality, output path, refs/masks if any.
- Capability reference: `skills/auto-mode/references/image-generation.md`.

## Iron Law

Generated asset claims require filesystem evidence: output paths, manifest, model/tool, prompt, size/aspect, quality, and failed jobs if any.

## Process

1. Read `skills/auto-mode/references/image-generation.md`.
2. Infer routine details from the task when safe: count, aspect/size, quality, stable descriptive filenames.
3. If missing detail fundamentally changes the output, return `NEEDS_CONTEXT` with the exact missing decision.
4. Use `scripts/generate-image.py` exclusively for generation.
5. Save outputs under the requested path, or `.claude/deliverables/<task-name>/images/` when unspecified.
6. Verify every claimed output file exists.
7. Return a manifest covering prompts, provider/tool, model, size/aspect, quality, count, refs/masks, output paths, failed jobs, provider errors, rate-limit or quality concerns, and retry recommendations.

## Prompt Work

Preserve the user's subject, style, constraints, text, brand, and references. Use concrete visual language: medium, composition, lighting, materials, texture, camera/view, layout. For text-heavy images, dense diagrams, labels, or multi-panel layouts, prefer high quality. For drafts/sweeps, prefer lower quality unless told otherwise.

For edits, preserve requested invariants and use provided reference images or masks.

## Output Contract

Return status `DONE`, `DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED`.

Include:

- `output_paths`: every generated file path.
- `manifest`: generation evidence and parameters.
- `concerns`: limitations, quality concerns, failed jobs, unavailable provider, or unverified acceptance refs.

For game assets, make the manifest additive and runtime-ready: asset_id, kind, output path, pixel size, logical size if used, transparency/background, scale, preview evidence, and concerns. For a sprite sheet/sprite strip include frame_width, frame_height, frame_count, layout columns/rows or strip direction, animation names, fps, loop, origin/anchor, and collision bounds/hitbox when relevant.

Never describe missing files as generated.
