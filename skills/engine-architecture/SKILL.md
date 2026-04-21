---
name: Engine Architecture
description: This skill should be used when designing game engine systems, including "ECS architecture", "entity component system", "rendering pipeline", "scene graph", "resource manager", "job system", "memory allocator", "engine module design", "plugin system", or any structural/engineering decision about how to organize engine internals. Also triggers when the user asks "how should I structure", "what pattern for", or "design the architecture for" engine subsystems.
---

# Game Engine Architecture Patterns

Guidance for designing robust, performant game engine systems in C++.

## Core Architectural Patterns

### Entity Component System (ECS)

The recommended pattern for game object composition:

- **Entity**: Lightweight ID (uint32_t or uint64_t), no data or logic
- **Component**: Plain data structs (POD), no virtual methods, cache-friendly
- **System**: Stateless functions operating on component views, processed in batches

```
// Component: pure data
struct TransformComponent {
    glm::vec3 position;
    glm::quat rotation;
    glm::vec3 scale;
};

// System: batch processing
void TransformSystem::update(World& world, float dt) {
    for (auto [entity, transform, velocity] :
         world.view<TransformComponent, VelocityComponent>()) {
        transform.position += velocity.direction * velocity.speed * dt;
    }
}
```

**Key ECS considerations:**
- Use sparse sets or archetypes for component storage (archetype for cache locality with many components, sparse set for fast add/remove)
- Prefetch memory when iterating large component arrays
- Keep components small and align to cache lines (64 bytes) for hot paths
- Use generation indices in entity IDs to detect stale references

### Memory Management

- **Stack allocator** for frame-scoped allocations (render commands, temp buffers)
- **Pool allocator** for fixed-size objects (components, events, particles)
- **Linear allocator** for bulk loading (resource parsing, asset loading)
- **Buddy allocator** or **free-list** for general-purpose heap allocation

**Pattern:** Override `operator new` per subsystem, never use global malloc in hot paths.

### Resource Management

Two-phase loading pattern:
1. **Synchronous header load** — Read metadata, create handle (fast)
2. **Async data load** — Stream bulk data in background thread

Reference-counted handles with weak references to detect dangling pointers:
```
template<typename T>
class ResourceHandle {
    uint32_t id;
    std::weak_ptr<ResourceEntry<T>> entry;
};
```

### Rendering Pipeline

Frame graph pattern for render pass management:
1. Declare render passes with inputs/outputs (textures, buffers)
2. Automatic barrier insertion and resource transition
3. Graph-based dependency resolution for parallel execution
4. Transient resource allocation (ring buffer for render targets)

### Job System

- Task-based parallelism with work-stealing scheduler
- Fork/join pattern for hierarchical parallelism
- Avoid locks in hot paths; use lock-free queues or atomic operations
- Batch small tasks into larger work items to amortize scheduling overhead

## Module Boundaries

Design each engine module as a self-contained unit:
- Public API through a facade class or C-style interface
- Internal implementation details hidden behind the API
- Minimal cross-module dependencies (prefer events/callbacks)
- Each module independently testable

**Typical module breakdown:**
```
core/          — Memory, containers, math, logging
platform/      — Window, input, filesystem, threading
renderer/      — GPU abstraction, shaders, pipeline
ecs/           — Entity component system
physics/       — Collision, rigid body, constraints
audio/         — Sound playback, spatial audio
resource/      — Asset loading, caching, hot-reload
scene/         — Scene graph, serialization
script/        — Lua/LuaJIT binding, scripting API
tools/         — Asset pipeline, exporters
```

## When to Read Further

- **`references/architecture-patterns.md`** — Detailed ECS implementation, frame graph, memory pool patterns
