# Game Engine Performance Guide Reference

## SIMD Patterns for Game Engines

### Vector Math with SSE/AVX

```
// 4-wide float vector operations
__m128 vec_add(__m128 a, __m128 b) { return _mm_add_ps(a, b); }
__m128 vec_mul(__m128 a, __m128 b) { return _mm_mul_ps(a, b); }

// Process 4 transforms simultaneously (SoA layout)
void transform_many(const float* positions, const float* velocities,
                    float* out, size_t count, float dt) {
    __m128 dt_v = _mm_set1_ps(dt);
    for (size_t i = 0; i < count; i += 4) {
        __m128 pos = _mm_load_ps(positions + i);
        __m128 vel = _mm_load_ps(velocities + i);
        __m128 result = _mm_add_ps(pos, _mm_mul_ps(vel, dt_v));
        _mm_store_ps(out + i, result);
    }
}
```

### Horizontal Operations

Avoid horizontal SIMD operations (hadd, dot product extraction) in inner loops. Instead, keep data in vector form and reduce only at the end.

## Memory Pool Implementation

```
template<typename T, size_t CHUNK_SIZE = 65536>
class MemoryPool {
    struct Chunk {
        alignas(alignof(T)) char data[CHUNK_SIZE * sizeof(T)];
        Chunk* next;
    };

    Chunk* chunks = nullptr;
    T* free_list = nullptr;

    T* allocate() {
        if (!free_list) expand();
        T* ptr = free_list;
        free_list = *reinterpret_cast<T**>(ptr);
        return ptr;
    }

    void deallocate(T* ptr) {
        *reinterpret_cast<T**>(ptr) = free_list;
        free_list = ptr;
    }

    void expand() {
        auto chunk = new Chunk();
        chunk->next = chunks;
        chunks = chunk;
        // Build free list
        for (size_t i = 0; i < CHUNK_SIZE - 1; ++i) {
            auto* ptr = reinterpret_cast<T*>(chunk->data + i * sizeof(T));
            *reinterpret_cast<T**>(ptr) = reinterpret_cast<T*>(chunk->data + (i + 1) * sizeof(T));
        }
    }
};
```

## Frame Profiler Design

### CPU Profiler

```
struct ProfileScope {
    const char* name;
    std::chrono::nanoseconds start;

    ProfileScope(const char* n) : name(n) {
        start = std::chrono::high_resolution_clock::now().time_since_epoch();
    }
    ~ProfileScope() {
        auto end = std::chrono::high_resolution_clock::now().time_since_epoch();
        Profiler::record(name, start, end - start);
    }
};

#define PROFILE_SCOPE(name) ProfileScope _profile_##name(#name)
```

### Frame Time Aggregation

- Ring buffer of last N frames (e.g., 300 = 5 seconds at 60fps)
- Per-system timing breakdown
- Report: mean, median, p95, p99, max
- Visual: TTF (Time To Frame) graph

### GPU Profiler

- Query timestamp differences between render pass begin/end
- Pipeline statistics queries (draw calls, triangles, fragments)
- Resolution: query results available 1-2 frames after submission

## Concurrency Patterns

### Lock-Free Ring Buffer (SPSC)

```
template<typename T, size_t SIZE>
class SPSCRingBuffer {
    std::array<T, SIZE> buffer;
    std::atomic<size_t> head{0};  // write position
    std::atomic<size_t> tail{0};  // read position

    bool push(const T& item) {
        size_t h = head.load(std::memory_order_relaxed);
        size_t next = (h + 1) % SIZE;
        if (next == tail.load(std::memory_order_acquire)) return false;
        buffer[h] = item;
        head.store(next, std::memory_order_release);
        return true;
    }

    bool pop(T& item) {
        size_t t = tail.load(std::memory_order_relaxed);
        if (t == head.load(std::memory_order_acquire)) return false;
        item = buffer[t];
        tail.store((t + 1) % SIZE, std::memory_order_release);
        return true;
    }
};
```

Use for: render thread command submission, audio buffer streaming, event queue.

### Work-Stealing Job System

- Global deque per thread (push/pop from owner thread, steal from others)
- Each job has a counter; wait on counter for completion
- Split large jobs into smaller chunks (divide-and-conquer)
- Avoid stealing too aggressively — affinity matters for cache locality

## False Sharing Prevention

```
// Bad: adjacent data modified by different threads
struct TaskState {
    std::atomic<int> progress;  // thread 0 writes
    std::atomic<int> completed; // thread 1 writes
};

// Good: pad to cache line boundary
struct alignas(64) TaskState {
    std::atomic<int> progress;
    char pad[60];
};

struct alignas(64) TaskCompletion {
    std::atomic<int> completed;
    char pad[60];
};
```

## Allocation Tracking

Instrument allocators to track:
- Total allocation count and size per frame
- Peak memory usage per subsystem
- Allocation frequency heatmap (which code paths allocate most)
- Use custom new/delete with source location tracking in debug builds
