# Game Engine Architecture Patterns Reference

## ECS Implementation Patterns

### Sparse Set Storage

Efficient for entities with many optional components (fast add/remove):

```
class SparseSet {
    std::vector<uint32_t> dense;    // packed array of entity IDs
    std::vector<uint32_t> sparse;   // entity ID -> index in dense
    std::vector<T>       data;      // component data, parallel to dense
};
```

- Add: O(1) — append to dense, update sparse mapping
- Remove: O(1) — swap with last, update sparse mapping
- Iterate: Cache-friendly sequential access over dense/data arrays
- Lookup: O(1) via sparse[entity] → index into dense/data

### Archetype Storage

Efficient for entities that share many components (optimal iteration):

```
struct Archetype {
    std::vector<ComponentType> type_signature;
    std::vector<void*>         component_arrays;
    std::vector<EntityId>      entities;
    size_t                     entity_count;
};
```

- Iterate over matching archetypes — all component data is contiguous
- Adding/removing a component type moves entity to a different archetype
- Best for queries over many components simultaneously

### Hybrid Approach

Use sparse sets for rarely-queried components and archetypes for hot-path queries.

## Frame Graph Pattern

### Render Pass Declaration

```
struct RenderPass {
    std::string name;
    std::vector<ResourceAccess> reads;   // resources consumed
    std::vector<ResourceAccess> writes;  // resources produced
    ExecuteFn execute;                   // render callback
};
```

### Resource Management

- Transient resources allocated from ring buffers (recycled each frame)
- Persistent resources (backbuffers, depth buffers) pre-allocated
- Automatic barrier insertion based on read/write access patterns

### Graph Compilation

1. Topological sort passes by dependency
2. Merge compatible passes (same render target, no overlap)
3. Insert synchronization barriers between incompatible passes
4. Allocate transient resources from ring buffer

## Memory Allocator Patterns

### Stack Allocator

```
class StackAllocator {
    void*  start;
    size_t capacity;
    size_t offset;
public:
    void* alloc(size_t size, size_t alignment);
    void  reset();  // clear entire stack (per-frame)
};
```

Use for: frame allocations, scratch memory, temporary buffers.

### Pool Allocator

```
template<typename T, size_t BlockSize = 4096>
class PoolAllocator {
    struct Block { T data; Block* next; };
    Block* free_list;
    std::vector<std::unique_ptr<char[]>> blocks;
};
```

Use for: fixed-size objects (entities, components, events, render commands).

### Linear Allocator

```
class LinearAllocator {
    void*  current;
    void*  end;
};
```

Use for: asset loading, string interning, one-way data processing. Cannot free individual allocations — reset all at once.

## Event System Pattern

```
template<typename... Args>
using EventCallback = std::function<void(Args...)>;

class EventBus {
    std::unordered_map<std::type_index, std::vector<std::any>> listeners;

    template<typename Event>
    void on(EventCallback<Event> callback);

    template<typename Event, typename... Args>
    void emit(Args&&... args);
};
```

- Type-safe, decoupled communication between modules
- Consider event priority ordering for critical systems
- Use for: input events, collision events, state change notifications
