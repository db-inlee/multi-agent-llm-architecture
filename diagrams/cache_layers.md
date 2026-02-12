# 4-Layer Cache Architecture

```mermaid
graph LR
    REQ([Incoming Request]) --> L1

    subgraph "Layer 1 — LLM Response Cache"
        L1[MemoryCache<br/>Key: MD5 of model+prompt<br/>TTL: 30min-1hr]
    end

    L1 -->|miss| L2

    subgraph "Layer 2 — RAG Cache"
        L2[RAGCache<br/>Key: MD5 of concern+skin_type<br/>TTL: 1hr]
    end

    L2 -->|miss| L3

    subgraph "Layer 3 — Function Cache"
        L3[SimpleCache<br/>Key: MD5 of args+kwargs<br/>TTL: configurable]
    end

    L3 -->|miss| L4

    subgraph "Layer 4 — Query Expansion LRU"
        L4[LRU Cache<br/>Key: tuple of concern fields<br/>Size: 128 entries]
    end

    L4 -->|miss| LLM[LLM API Call]

    L1 -->|hit| RES([Cached Response])
    L2 -->|hit| RES
    L3 -->|hit| RES
    L4 -->|hit| RES

    style L1 fill:#4a90d9,color:#fff
    style L2 fill:#f5a623,color:#fff
    style L3 fill:#7b68ee,color:#fff
    style L4 fill:#2ecc71,color:#fff
```

## Key Design: No `session_id` in Cache Keys

Cache keys deliberately **exclude session_id** so that identical queries from
different users share the same cache entry. This is why warm-path TTFT can drop
below 1 second for CS/Reco — the first user "primes" the cache for everyone.

```
memory_cache : MD5(model | system_prompt | user_prompt)
rag_cache    : MD5(concern | skin_type | primary_concern)
simple_cache : MD5(JSON(args, kwargs))
lru_cache    : tuple(primary_concern, skin_type, concerns_key, avoid_key)
```
