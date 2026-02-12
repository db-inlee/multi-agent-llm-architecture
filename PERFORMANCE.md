# Performance Engineering

## TL;DR

- 6가지 최적화 기법 + 4-layer 캐시로 warm-path E2E 50-60% 감소
- 핵심: routing 구조 재설계로 턴당 LLM 호출 5회 → 0-2회 (p50). → 설계 판단: [DECISIONS.md § 1](DECISIONS.md)
- CS TTFT 20.8s → 0.9s (-95.7%), Skincare Turn 1 TTFT ~20s → 2.4s (-88%)
- 캐시 없이도 코드 최적화만으로 TTFT 22-88% 감소 (벤치마크 2)
- 시스템 구조: [ARCHITECTURE.md](ARCHITECTURE.md) · 설계 판단: [DECISIONS.md](DECISIONS.md)

6가지 최적화 기법과 4-layer 캐시를 조합해 warm path 기준 E2E 지연시간 **50-60%** 감소.

이 시스템은 멀티 에이전트 라우팅 + RAG + 슬롯 수집을 거치는 의사결정 파이프라인이다. 구조상 cold latency가 높을 수밖에 없다. 따라서 cold 최소화보다 **warm path 안정화**에 설계 초점을 두었다 — 반복 질의에서 LLM 호출 자체를 줄이고, 캐시와 rule-based 분기로 실제 운영 상태의 응답 속도를 확보하는 것이 목표다.

---

## 벤치마크 1: Cache Cold → Warm

| Agent | TTFT Cold → Warm | E2E Cold → Warm | 개선율 |
|---|---|---|---|
| CS | 20,838ms → **905ms** | 29,957ms → 10,129ms | TTFT **-95.7%** |
| Reco | 16,825ms → **1,928ms** | 27,743ms → 12,238ms | TTFT **-88.5%** |
| AS | 5,431ms → **3,687ms** | 9,518ms → 7,383ms | TTFT **-32.1%** |
| Skincare | 5,828ms → 5,100ms | 7,735ms → 7,121ms | TTFT -12.5% |
| Supervisor | 42,704ms → **1,453ms** | 55,971ms → 12,581ms | TTFT **-96.6%** |

코드 최적화가 모두 적용된 동일 코드 위에서 캐시 on/off만 전환한 비교. Cold = 최적화된 코드 + 캐시 미적용, Warm = 최적화된 코드 + 캐시 적용.

전체 벤치마크: [benchmarks/cache_cold_warm.md](benchmarks/cache_cold_warm.md)

---

## 벤치마크 2: 최적화 전 → 후 (Warm 기준)

| Agent | Turn | Before TTFT | After TTFT | 개선율 |
|---|---|---|---|---|
| Skincare | Turn 1 | ~20,000ms | 2,419ms | **-88%** |
| Skincare | Turn 2 | 9,900ms | 3,256ms | **-67%** |
| Reco | Turn 1 | 14,064ms | 10,964ms | **-22%** |
| Reco | Turn 2 | 32,999ms | 12,544ms | **-62%** |

캐시 조건을 동일하게 고정(Warm)한 상태에서, 코드 최적화(기법 1-5) 적용 전후만 비교. 캐시 효과가 아니라 routing 구조 재설계와 LLM 호출 감소의 순수 효과를 측정한 결과다.

---

## 기법 1: Quick-Path 슬롯 추출

**문제**: LLM 슬롯 추출(`_invoke_json`)이 건당 7-9초 소요. "지성인데 모공이 고민이에요" 같은 단순 입력에 이걸 쓰는 건 낭비다.

**해법**: 2단계 추출. 정규식/키워드로 `concerns`와 `skin_type`을 모두 잡으면 7초짜리 LLM 호출이 제거된다. 부분 매칭도 효과가 있다 — `skin_type`만 없으면 LLM 없이 "collect" 응답을 반환한다.

<details>
<summary>처리 흐름</summary>

```
유저: "지성인데 모공이 고민이에요"
  ↓
1단계: 정규식 → skin_type = "oily"         (<10ms)
       키워드 스캔 → concerns = ["pore"]    (<10ms)
  ↓
필수 슬롯 전부 충족 → _invoke_json 호출 자체를 건너뜀
  ↓
가벼운 의도 분류만 실행                       (~500ms)
```

</details>

**효과**: slot_collector 노드 기준 7-9s → 0-2s.

→ `skeleton/agents/skincare/slots.py` 참조

---

## 기법 2: 병렬 LLM 호출 (ThreadPoolExecutor)

**문제**: 의도 분류와 에이전트 선택은 독립적인 판단인데, 순차 실행하면 ~3.5초 소요.

**해법**: `ThreadPoolExecutor(max_workers=2)`로 동시 실행. LLM API 호출은 I/O bound 작업이므로 ThreadPool 기반 병렬화가 latency 감소에 유효하다. `check_completeness` + `decide_next_step`에도 동일 패턴 적용.

<details>
<summary>구현 예시</summary>

```python
def classify_intent_and_select_agent_parallel(self, state):
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_intent = pool.submit(self.classify_intent, state)
        f_agent  = pool.submit(self.select_agent, state)
        return f_intent.result(), f_agent.result()
```

</details>

**효과**: 첫 턴 라우팅에서 ~1.5s 절감, 이후 턴에서 ~300ms 절감.

---

## 기법 3: 첫 턴 빠른 경로

**문제**: 첫 메시지에는 대화 컨텍스트가 없다. 핸드오프 검사, 완결성 분석, 다음 단계 판단을 돌리는 건 의미 없다 — 핸드오프할 이전 에이전트도, 체크할 완결성도 없으니까.

**해법**: 4-case 라우터의 Case 1에서 5개 LLM 호출 중 3개를 스킵. → 라우터 구조: [ARCHITECTURE.md § 4-Case 조건부 라우팅](ARCHITECTURE.md)

| 풀 라우팅 (5 호출) | 첫 턴 (2 호출) |
|---|---|
| classify_intent | classify_intent |
| select_agent | select_agent |
| ~~decide_handoff~~ | 스킵 |
| ~~check_completeness~~ | 스킵 |
| ~~decide_next_step~~ | 스킵 |

**효과**: 첫 메시지 라우팅 지연시간 ~40% 감소.

---

## 기법 4: Waiting-Stage 스킵

**문제**: 에이전트가 사용자 입력을 기다리는 중일 때 (예: "피부 타입이 뭔가요?"), 사용자의 다음 메시지는 그 질문에 대한 답일 뿐이다. 여기에 풀 라우팅을 돌리면 5초 이상 낭비.

**해법**: 에이전트의 대기 상태를 감지하고 LLM 라우팅 호출을 전부 건너뛴다. 감지되면 라우터가 rule-based decision을 즉시 반환: intent는 현재 에이전트 매핑, completeness = incomplete, next_step = "process". LLM 호출 0회.

단, 주제 변경 감지가 먼저 실행된다 — 사용자가 답변 대신 주제를 바꾸면 빠른 경로를 우회하고 풀 라우팅으로 진입한다.

<details>
<summary>에이전트별 대기 상태</summary>

```
에이전트별 대기 상태:
  CS:       ["wait_user"]
  AS:       ["wait_confirm", "wait_product", "wait_symptom", ...]
  Skincare: ["clarify", "offer"]
  Reco:     ["NEED_MORE_INFO"]
```

</details>

**효과**: 에이전트 대기 상태에서 턴당 -5s.

---

## 기법 5: How-To 스킵

**문제**: 정보성 질문 ("선크림 어떻게 레이어링해요?")에 전체 스킨케어 파이프라인을 돌릴 필요가 없다. 루틴 합성, 긴급도 분석, scope consistency guard는 불필요한 오버헤드.

**해법**: `question_type == "how_to"` 감지 시 스킵:

| 스킵 노드 | 이유 |
|---|---|
| routine_synthesizer | 루틴을 요청한 게 아님 |
| urgency analysis (conversational_response 내) | 의학적 우려 없음 |
| scope_consistency_guard | How-to는 넓은 지식베이스에 매칭됨 |

**효과**: 정보성 질문에서 ~3-4s 절감.

---

## 기법 6: 4-Layer 캐시 + Cross-User 공유

**문제**: LLM 호출이 비용의 대부분을 차지한다. 많은 사용자가 비슷한 질문을 하는데, 세션별 캐싱은 모든 사용자가 전체 지연을 감수해야 한다.

**해법**: session_id를 포함하지 않는 캐시 키로 4개 레이어를 구성한다. → 이 설계의 판단 근거: [DECISIONS.md § 2](DECISIONS.md)

| 레이어 | 범위 | 키 설계 | TTL |
|---|---|---|---|
| **MemoryCache** | LLM 라우팅 + 응답 | `MD5(model \| system_prompt \| user_prompt)` | 30분–1시간 |
| **RAGCache** | FAISS 검색 결과 | `MD5(concern \| skin_type \| primary_concern)` | 1시간 |
| **SimpleCache** | 함수 레벨 메모이제이션 | `MD5(JSON(args, kwargs))` | 설정 가능 |
| **LRU Cache** | 쿼리 확장 | `tuple(primary_concern, skin_type, ...)` | 128 엔트리 |

핵심: 캐시 키는 **정규화된 질의와 프롬프트 기준**으로 생성하며 `session_id`를 포함하지 않는다. 캐싱 대상은 LLM 라우팅 결과와 RAG 검색 결과이며, 개인화 컨텍스트는 포함되지 않는다. 사용자 A가 "건성 피부 보습제"를 물어보고, 5분 뒤 사용자 B가 같은 질문을 하면 캐시 히트가 발생한다. CS의 warm-path TTFT가 20.8s에서 1초 미만으로 떨어지는 이유다. 질문 패턴과 라우팅 프롬프트가 사용자 간 거의 동일하다는 전제에서 설계했다.

**효과**: 캐시 친화적 질문에서 TTFT 최대 95.7% 감소.

→ `skeleton/common/memory_cache.py`, `skeleton/agents/skincare/rag/cache.py`, `diagrams/cache_layers.md` 참조

---

## 종합 효과

warm 시스템 + 일반적 질문 분포 기준:

warm 성능은 캐시 단독 효과가 아니라 quick-path(기법 1), 병렬화(기법 2), waiting-stage skip(기법 4), how-to skip(기법 5), cache(기법 6)가 결합된 결과다.

| 지표 | Before (코드 최적화 전) | After (코드 최적화 + Warm cache) | 감소율 |
|---|---|---|---|
| 평균 TTFT (warm) | ~15s | ~2-3s | **80%+** |
| 평균 E2E (warm) | ~20s | ~8-10s | **50-60%** |
| 턴당 LLM 호출 (p50) | 5 | 0-2 | **60-100%** |
| 턴당 LLM 호출 (p95) | 5 | 3-5 | **0-40%** |

최적화가 복합적으로 작용한다: 재방문 사용자가 warm 시스템에서 자주 묻는 질문을 하면 캐시(기법 6)를 타고, LLM 라우팅을 통째로 건너뛰고(기법 4), 슬롯을 정규식으로 추출(기법 1)해서 TTFT가 1초 미만으로 내려간다.

가장 큰 개선 요인은 개별 기법이 아니라 **routing 구조 자체를 재설계해서 턴당 LLM 호출 횟수를 5회에서 0-2회(p50 기준)로 줄인 것**이다. 캐시는 그 위에 얹힌 가속 레이어이며, 캐시 없이도 코드 최적화만으로 TTFT 22-88% 감소를 달성한다(벤치마크 2 참조). → 라우팅 구조 설계 판단: [DECISIONS.md § 1](DECISIONS.md)
