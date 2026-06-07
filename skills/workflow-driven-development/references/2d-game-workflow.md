# 2D Game Workflow

Use this reference when a workflow task builds or plans a 2D browser game. It adapts the game-studio guidance into Claude Code Flow's existing plan → implement → review pipeline.

## Default Stack

Default to Phaser for 2D browser games unless the spec names another engine. Good fits: sprites, tilemaps, top-down movement, side-view action, turn-based grids, tactics, arcade loops, and lightweight management scenes.

Use TypeScript/Vite conventions when the generated project has no stronger existing stack. Do not add Phaser to an existing app if the user explicitly chose another runtime.

## Architecture Boundary

Keep gameplay state outside the renderer.

- Simulation owns rules, entities, movement, collisions, turns, timers, combat, inventory, progression, objectives, and saveable state.
- Renderer owns Phaser scenes, sprites, animation playback, camera, particles, tweens, and presentation effects.
- Input maps physical controls to semantic actions before simulation consumes them.
- UI owns dense text, menus, settings, command panels, inventory, and accessibility-sensitive controls.

Renderer objects are disposable view state. Save serializable simulation state, not Phaser sprites, tweens, emitters, cameras, or DOM nodes.

## Default Directory Shape

```text
src/
  game/
    simulation/
      state.ts
      systems/
      rules/
    content/
      encounters/
      items/
      maps/
    input/
      actions.ts
      bindings.ts
    assets/
      manifest.ts
  phaser/
    boot/
    scenes/
      BootScene.ts
      MenuScene.ts
      GameplayScene.ts
    view/
      sprites/
      fx/
      camera/
    adapters/
      sceneBridge.ts
  ui/
    hud/
    menus/
    overlays/
```

Responsibilities:

- `src/game/simulation` is the source of truth for rules and saveable state.
- `src/game/input` defines the input action map and physical bindings.
- `src/game/assets/manifest` defines stable asset keys and metadata.
- `src/phaser/scenes` orchestrates boot, preload, menu, and gameplay scenes; it does not own game rules.
- `src/phaser/adapters/sceneBridge.ts` is the integration boundary between scene events and simulation actions.
- `src/ui` renders DOM HUD, menus, overlays, settings, and narrative panels.

## Planning Checklist

Before coding, the plan should lock:

- player fantasy and primary verbs
- core loop, failure state, recovery/reset, and target session length
- camera model: locked, follow, room-based, tactical-pan, or side-view
- input action map: move, confirm, cancel, attack, ability, pause, menu navigation
- simulation modules and serializable state shape
- renderer modules and scene lifecycle
- DOM HUD/menu surfaces and responsive behavior
- asset manifest keys and asset groups: characters, environment, ui, fx, audio, data
- test path: unit tests for simulation, integration tests for adapters, smoke/playtest for runtime

## Sprite and Image Assets

Do not duplicate image provider logic in game tasks. Use `claude-code-flow:image-generation` for sprite or image creation/editing.

For 2D sprite animations:

1. Start from one approved in-game seed frame.
2. Generate the whole strip in one image task, not independent frames.
3. Preserve facing direction, silhouette family, palette family, proportions, readable key features, and transparent background.
4. Normalize with one shared scale and one shared anchor, usually bottom-center.
5. Optionally lock frame 01 back to the shipped seed frame.
6. Preview before wiring the asset into `src/game/assets/manifest.ts`.

Implementation tasks should consume returned image paths and manifests only after the image task reports files exist.

## UI Rules

Use a DOM HUD by default for text-heavy or accessibility-sensitive surfaces. Keep the canvas focused on the playfield.

- Critical status first; secondary tools behind menus, drawers, or pause surfaces.
- Keep center playfield mostly clear during normal play.
- Prefer transient hints over permanent instruction blocks.
- Respect reduced-motion settings for non-essential animation.
- Gate gameplay input while menus, dialogs, or command panels are active.

## Playtest Gate

Runnable 2D game deliverables need a browser smoke/playtest pass when possible. Check:

- game boots into a useful first state
- main verbs are obvious and responsive
- HUD remains readable over gameplay
- central playfield stays clear
- pause, failure, and recovery states work
- viewport resize does not break layout
- sprite baseline, hit/hurt/attack timing, command focus, tile/platform readability
- camera shake, particles, and effects do not obscure gameplay

Record likely owner for findings: simulation, renderer, frontend, or asset pipeline.

## Review Checklist

Spec and code reviewers should reject:

- gameplay rules embedded directly in Phaser `update()` with no simulation boundary
- Phaser scenes or sprites treated as saveable source of truth
- asset file paths scattered through gameplay code instead of stable manifest keys
- DOM-suitable HUD/menu work forced into canvas without a spec reason
- image generation attempted outside `claude-code-flow:image-generation`
- sprite strips wired before output files/manifests exist
- runnable games marked complete without smoke/playtest evidence or an explicit unverifiable note
