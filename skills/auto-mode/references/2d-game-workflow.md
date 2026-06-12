# 2D Game Workflow

Use when auto-mode builds or plans a 2D browser game.

## Default Stack

Default to Phaser for 2D browser games unless the spec names another engine. Use TypeScript/Vite conventions when no stronger existing stack exists. Do not add Phaser to an existing app if the user chose another runtime.

## Architecture Boundary

Keep gameplay state outside the renderer.

- Simulation owns rules, entities, movement, collisions, turns, timers, combat, inventory, progression, objectives, and saveable state.
- Renderer owns Phaser scenes, sprites, animations, camera, particles, tweens, and presentation effects.
- Input maps physical controls to semantic actions before simulation consumes them.
- UI owns dense text, menus, settings, command panels, inventory, and accessibility-sensitive controls.

Save serializable simulation state, not Phaser sprites, tweens, emitters, cameras, or DOM nodes.

## Default Shape

```text
src/
  game/
    simulation/
    content/
    input/
    assets/manifest.ts
  phaser/
    scenes/
    view/
    adapters/sceneBridge.ts
  ui/
    hud/
    menus/
    overlays/
```

## Planning Checklist

Lock player fantasy, primary verbs, core loop, failure/recovery, camera model, input action map, simulation modules, renderer modules, DOM HUD/menu surfaces, asset manifest keys, and test path.

## Sprite and Image Assets

Use `image-generation.md` for sprite or image creation/editing.

For 2D sprite animations:

1. Start from one approved in-game seed frame.
2. Generate the whole strip in one image task, not independent frames.
3. Preserve facing direction, silhouette family, palette family, proportions, readable features, transparent background.
4. Normalize with one shared scale and bottom-center anchor.
5. Preview before wiring the asset into `src/game/assets/manifest.ts`.

Implementation tasks consume returned image paths and manifests only after files exist.

## Review Checklist

Reject gameplay rules embedded directly in Phaser `update()`, Phaser scenes/sprites treated as saveable truth, scattered asset paths instead of manifest keys, DOM-suitable HUD forced into canvas without reason, sprite strips wired before files/manifests exist, or runnable games marked complete without smoke/playtest evidence.

## Scope and Runtime Detection

Use this workflow for 2D browser games. Greenfield ambiguous small 2D browser game requests may default to prompt-only Phaser + TypeScript + Vite. Preserve explicit user choices and existing stacks first: React/canvas, plain TypeScript canvas, Three.js, custom engines, or named non-browser runtimes such as Unity, Godot, Bevy, Pygame, terminal, or server simulation. Do not add Phaser, Vite, browser screenshots, or new repo dependencies when an existing runtime conflicts.

Detection precedence: current user request, package/source imports and scripts, existing game files or asset registry, accepted design/spec for this run, then greenfield default.

Ask or scope down for native/mobile-first/touch, multiplayer/accounts/leaderboards, monetization, licensed/external assets, production art/audio, save/load/progression, level editors, deployment, or conflicting engines. Assume only routine defaults: desktop browser, keyboard controls, one playable core loop, one arena/screen, simple code-drawn placeholders, silence unless audio is requested, and no persistence unless requested.

## Design Trigger and Mixed Work

Run Design for visible playable canvas changes, HUD, menus, overlays, controls/input UX, camera/readability, visual feedback, or asset presentation. Skip Design for pure simulation/rules/data/docs/config/test-only/internal refactors. Split mixed requests: simulation tasks can stay internal while HUD/playable surface tasks use accepted Design refs.

## Game Data Contract

Simulation owns serializable rules/entities/collisions/timers/objectives/progression when those concepts exist. Input maps physical keys/buttons to semantic actions before simulation. Renderer consumes read-only snapshots/projections and emits semantic actions/events. DOM owns dense text, forms, settings, inventory, menus needing focus, and accessibility-sensitive controls. Canvas HUD is acceptable for simple score/health/ammo overlays with rationale.

Phaser Arcade/engine physics is acceptable for tiny arcade MVP collision/movement when no persistence/replay/testing boundary is needed. Separate simulation/state modules when multiple mechanics, score/timer progression, inventory, persistence, replay, deterministic tests, or saveable state matter.

## Plan Task Dependency Pattern

Split tasks where applicable: data-contract, simulation, input map, artist assets, asset manifest/preload, renderer adapter, HUD/UI, playtest evidence. Runnable browser tasks need `Acceptance refs:`, `Runtime evidence required: required`, concrete verification commands, and evidence via screenshots/logs/artifacts or explicit `unverified_acceptance_items` and `blocking_risks`.

## Asset Handoff Contract

Use `image-generation.md` and `artist-prompt.md` for file assets. Artist output must include asset_id, kind, output path, pixel size, logical size if used, transparent/background info, scale, preview path or directly previewable output, and concerns. Sprite sheet metadata must include frame_width, frame_height, frame_count, layout columns/rows or strip direction, animation names, fps, loop, origin/anchor, and collision bounds when relevant.

Preview before wiring: verify generated files exist and have a preview artifact before imports, preload maps, or `src/game/assets/manifest.ts` wiring. If provider/auth fails, never claim final art. Use explicit placeholders with concerns, leave temp/draft outputs unwired, or report `DONE_WITH_CONCERNS`.

## Browser Smoke/Playtest Evidence

Gate 4 for runnable browser games must verify build/start, route load, render surface/canvas, semantic inputs from acceptance refs, core-loop observation, conditional failure/restart, conditional asset load, console status, crash/hang, and screenshot evidence when browser tooling permits. Logs alone cannot clean-pass visual refs; list unverified visual refs instead.

Default route for greenfield Vite is `/`. Existing apps use detected/spec route. Prefer `.claude/artifacts/auto-mode/<run-or-task-id>/` for screenshots, logs, and playtest notes. Use a bounded smoke/playtest timeout, normally 30-120s. Final summaries should include: `Runtime evidence: <commands>; <playtest observation>; artifacts: <screenshots/logs/artifacts or none>; unverified: <refs or none>`.
