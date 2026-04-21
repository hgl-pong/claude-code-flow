---
name: Engine Performance
description: This skill should be used when the user asks about "game engine performance", "optimization", "profiling", "memory usage", "cache locality", "data-oriented design", "multithreading", "SIMD", "reduce allocations", "frame time", "GPU performance", "draw call batching", "instancing", or any performance-related topic in game engine development. Also triggers when diagnosing performance issues, implementing profiling systems, or writing benchmarking code.
---

# Game Engine Performance Optimization

Strategies for achieving real-time performance in game engines built with C++.

## Data-Oriented Design

Structure data for CPU cache efficiency, not for object-oriented aesthetics.

**Principles:**
- Process components in contiguous arrays (Structure of Arrays over Array of Structures)
- Keep hot data together, cold data separate
- Avoid pointer chasing in inner loops
- Align frequently accessed data to cache line boundaries (64 bytes)

```
// Bad: AoS — scattered memory access
struct GameObject {
    glm::vec3 position;  // hot
    std::string name;    // cold
    glm::vec3 velocity;  // hot
    std::vector<Component*> components;  // cold
};

// Good: SoA — sequential memory access
struct PositionData { std::vector<glm::vec3> values; };
struct VelocityData { std::vector<glm::vec3> values; };
struct Metadata     { std::vector<std::string> names; };
```

## Memory Optimization

### Allocation Reduction
- Pre-allocate buffers at startup; avoid per-frame heap allocation
- Use object pools for frequently created/destroyed objects
- Custom allocators per subsystem with bounded memory budgets
- Small string optimization or fixed-string for names/tags

### Fragmentation Prevention
- Allocate from segregated size classes (8, 16, 32, 64, 128, 256, 512, 1024 bytes)
- Use linear/stack allocators for temporary data (reset each frame)
- Compact defragmentation during load screens, not during gameplay

## CPU Performance

### Profiling Approach
1. Instrument hot paths with CPU timestamps (rdtsc or std::chrono)
2. Aggregate per-frame timing into ring buffers for statistical analysis
3. Visualize frame time breakdown (TTF — Time To Frame)
4. Profile before optimizing; measure after optimizing

### Concurrency
- Task graph with explicit dependencies for parallel job scheduling
- Avoid false sharing — pad shared data to cache line boundaries
- Use atomic operations instead of mutexes for simple counters/flags
- Lock-free ring buffers for producer-consumer patterns (render thread communication)

### SIMD
- Use SSE/AVX intrinsics for vector math (4-wide float operations)
- Process data in batches of 4/8 elements
- SoA layout naturally enables SIMD vectorization
- Compiler auto-vectorization works better with aligned data and simple loops

## GPU Performance

### Draw Call Reduction
- Instancing for repeated geometry (trees, particles, UI elements)
- Static/dynamic batching for small meshes
- Texture atlases to reduce material switches
- Sort draw calls by material/pipeline state to minimize state changes

### Bandwidth Optimization
- Texture compression (BC/ASTC formats)
- Mipmapping for all textures (reduces cache miss rate on GPU)
- Use conservative depth to avoid unnecessary fragment shading
- Compute shaders for particle systems and culling

### Shader Optimization
- Minimize register pressure (reduce live variables)
- Avoid divergent branching in fragment shaders
- Use wave/warp-level operations (ballot, shuffle) where applicable
- Prefer arithmetic over texture lookups in hot loops

## Benchmarking

Write benchmarking utilities that:
- Run N iterations, discard outliers, report mean/median/p99
- Warm up caches before measuring
- Isolate subsystems (test rendering without physics, etc.)
- Compare against previous baseline to catch regressions

## When to Read Further

- **`references/performance-guide.md`** — Detailed SIMD patterns, memory allocator implementations, frame profiler design
