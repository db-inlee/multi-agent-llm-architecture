# Cold-path vs Warm-path Cache Benchmark

## Test Setup
- **Server**: FastAPI + LangGraph Multi-Agent Orchestrator (local, single process)
- **Model**: gpt-4o-mini
- **Method**: streaming=true, 3 warmup rounds excluded, 5-run average
- **Cache clear**: `POST /debug/cache/clear` — clears all 4 in-memory cache layers
  - MemoryCache (LLM routing/response), RAGCache (retrieval), SimpleCache (function-level), LRU (query expansion)

---

## 1. Latency Comparison (5-run avg, ms)

| Agent | Scenario | Cold TTFT | Warm TTFT | Cold E2E | Warm E2E |
|:---:|---|---:|---:|---:|---:|
| Skincare | Pore concern (slot+RAG) | 5,828 | 5,100 | 7,735 | 7,121 |
| Reco | Product recommendation | 16,825 | 1,928 | 27,743 | 12,238 |
| Skincare | Informational (how-to) | 15,136 | 15,406 | 18,750 | 19,130 |
| AS | Device power issue | 5,431 | 3,687 | 9,518 | 7,383 |
| CS | Product usage inquiry | 20,838 | 905 | 29,957 | 10,129 |
| Supervisor | Skincare + Reco compound | 42,704 | 1,453 | 55,971 | 12,581 |

## 2. Cache Effect (Cold → Warm Improvement)

| Agent | Scenario | TTFT Improvement | E2E Improvement | Cache Hit Rate |
|:---:|---|---:|---:|---:|
| **CS** | Product usage | **-95.7%** | **-66.2%** | 80.0% |
| **Reco** | Product reco | **-88.5%** | **-55.9%** | 66.7% |
| **AS** | Device issue | **-32.1%** | **-22.4%** | 60.0% |
| Skincare | Pore concern | -12.5% | -7.9% | 33.3% |
| Skincare | How-to | +1.8% | +2.0% | 45.0% |
| **Supervisor** | Skincare + Reco | **-96.6%** | **-77.5%** | 66.7% |

## 3. Analysis

**Cold-path** = no cache, pure processing cost.
**Warm-path** = cache active, production-like performance.

| Pattern | Explanation |
|---|---|
| **CS / Reco** | MemoryCache hit skips the entire LLM routing + response chain → TTFT **under 1s** |
| **AS** | Router cache hit saves the intent classification call → 32% TTFT reduction |
| **Skincare (pore)** | Per-turn slot changes cause partial cache misses → modest gain |
| **Skincare (how-to)** | RAG cache hits (45%) but downstream LLM calls dominate → no net improvement |
| **Supervisor** | Cold path is the slowest (~56s) due to plan + dual-agent execution; warm path MemoryCache hits skip routing → TTFT **under 1.5s**, E2E **-77.5%** |

## 4. Cache Key Design (cross-user sharing)

```
memory_cache : MD5(model | system_prompt | user_prompt)
rag_cache    : MD5(concern | skin_type | primary_concern)
simple_cache : MD5(JSON(args, kwargs))
lru_cache    : tuple(primary_concern, skin_type, concerns_key, avoid_key)
```

> Keys deliberately **exclude session_id** — identical queries from different users share cache entries.
> This is how CS/Reco warm TTFT drops below 1 second: the first user primes the cache for everyone.
