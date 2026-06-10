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
