# Architecture Overview

## TL;DR

- 4-layer 구조: API → ChatService → Orchestrator(4-case 라우터) → Agent(4종)
- Orchestrator는 ~30필드 Pydantic 상태 모델을 중앙 관리하고, 에이전트는 내부 상태를 독립적으로 관리
- Skincare Agent가 가장 복잡 (9노드 서브그래프 + FAISS RAG 7모듈)
- Supervisor 패턴으로 멀티 intent 질의를 병렬 실행 후 통합
- Infrastructure: Redis(세션+캐시), ContextVar 트레이싱, 노드별 메트릭, 표준화된 LLM 호출 계층
- 설계 판단 근거: [DECISIONS.md](DECISIONS.md) · 성능 최적화: [PERFORMANCE.md](PERFORMANCE.md)

## 시스템 레이어 구조

```
┌──────────────────────────────────────────────┐
│  API Layer — FastAPI + SSE 스트리밍            │
├──────────────────────────────────────────────┤
│  Chat Service — PipelineTracer, 토큰 스트림    │
├──────────────────────────────────────────────┤
│  Orchestrator — LangGraph StateGraph          │
│    ├── LLM Router (4-case 조건부 분기)         │
│    ├── Agent Dispatcher                       │
│    └── Supervisor (plan/execute/validate)      │
├──────────────────────────────────────────────┤
│  Agent Layer                                  │
│    ├── Skincare (9-node 서브그래프 + FAISS)    │
│    ├── Reco (슬롯→검색→재랭킹→응답)            │
│    ├── AS (A/S 접수 + 선형 슬롯 수집)          │
│    └── CS (이슈분류 + RAG + 외부API)           │
├──────────────────────────────────────────────┤
│  Infrastructure                               │
│    ├── 4-layer 캐시 (cross-user 공유)          │
│    ├── PipelineTracer (ContextVar 스팬)        │
│    ├── MetricsStore (노드별 타이밍)             │
│    ├── Redis (세션 저장 + 캐시)                 │
│    └── OpenAILLM + LLMCallBuilder              │
└──────────────────────────────────────────────┘
```

---

## 1. Orchestrator Layer

### OrchestratorState

그래프 전체를 관통하는 중앙 상태 객체. 약 30개 필드로 구성된 상태 모델이며, 라우팅 및 핸드오프 판단에 필요한 상태 정보를 중앙에서 관리한다.

<details>
<summary>주요 필드 그룹</summary>

- **세션**: session_id, thread_id, user_id, language
- **입력**: user_text, conversation_history, conversation_turns
- **메모리**: user_profile, relevant_memories, is_returning_user
- **판단**: intent_decision, agent_decision, handoff_decision, completeness_decision, next_step_decision
- **핸드오프 guardrail**: pending_handoff, handoff_chain, handoff_count (반복 전환 방지)
- **에이전트 상태**: current_agent, previous_agent, agent_states, shared_context
- **Supervisor**: supervisor_plan, supervisor_validation, agent_results
- **응답**: response_text, response_metadata, needs_user_input, is_complete

</details>

→ `skeleton/orchestrator/schemas.py` 참조

### 4-Case 조건부 라우팅

라우터는 대화 상태를 보고 latency 및 호출 비용이 가장 낮은 실행 경로를 선택한다. → 이 구조를 선택한 이유: [DECISIONS.md § 1](DECISIONS.md)

| Case | 조건 | LLM 호출 수 | 동작 |
|---|---|---|---|
| **1 — 첫 턴** | `conversation_turns == 0` | 2 (병렬) | 의도 + 에이전트 선택만 |
| **2 — 핸드오프** | 에이전트가 핸드오프 시그널 | 3 (순차) | 의도 → 에이전트 → 핸드오프 확인 |
| **3 — 같은 에이전트** | 동일 에이전트 연속 | 0–3 (가변) | 하위 분기 참조 |
| **4 — 풀 라우팅** | 복잡한 경우 / fallback | 4 (최적화) | 전체 결정 |

<details>
<summary>Case 3 하위 분기 (운영 빈도 최고 구간)</summary>

| 하위 케이스 | LLM 호출 | 로직 |
|---|---|---|
| Pending handoff | 0 | 사용자의 에이전트 전환 수락/거절 처리 |
| Waiting stage | 0 | 에이전트가 정보 요청 중 — 전부 스킵 |
| 의도 변경 감지 | 1 | PendingHandoff 생성, 사용자에게 확인 요청 |
| 일반 계속 | 2 (병렬) | completeness + next_step |

</details>

### 핸드오프 Guardrail

에이전트 간 반복 전환(loop)을 방지하기 위한 3중 장치. → 설계 판단: [DECISIONS.md § 4](DECISIONS.md)

1. **핸드오프 체인 추적**: `handoff_chain`에 모든 전환 이력 기록
2. **루프 감지**: `handoff_count >= 3`이면 CS로 fallback
3. **PendingHandoff 타임아웃**: 2분 내 사용자 응답 없으면 자동 해제, 현재 에이전트로 계속

---

## 2. Agent Layer

### BaseAgentAdapter 패턴

모든 에이전트가 오케스트레이터에 동일한 인터페이스를 노출한다. 오케스트레이터는 에이전트 내부 상태에 절대 접근하지 않는다 — `user_text`를 넣고 `response_text`를 읽을 뿐이다. 각 에이전트는 자체 체크포인트를 독립적으로 관리한다. → 분리 판단: [DECISIONS.md § 5](DECISIONS.md)

<details>
<summary>인터페이스 코드</summary>

```python
class BaseAgentAdapter(ABC):
    @abstractmethod
    def process(self, state: OrchestratorState) -> OrchestratorState:
        """user_text를 받아서 response_text를 채워 반환. 내부 상태는 에이전트가 자체 관리."""

    @abstractmethod
    def extract_slots(self, user_text, context) -> dict:
        """전체 파이프라인 실행 없이 도메인 슬롯만 추출."""
```

</details>

### Skincare Agent — 9-Node 파이프라인

멀티턴 상태 기반 처리로 인해 노드 수가 가장 많은 에이전트. 근거 기반 멀티턴 스킨케어 상담을 처리한다.

```
slot_collector → symptom_probe → evidence_retriever
    → scope_consistency_guard → [web_fallback]
    → conversational_response → offer_gate
    → [routine_synthesizer] → finalize → conversation_router
```

주요 특징:
- **Quick-path 슬롯 추출**: 정규식으로 skin_type과 concerns를 먼저 잡는다. 필수 슬롯이 모두 채워지면 latency cost가 높은 `_invoke_json` 호출을 통째로 건너뛴다. → 성능 효과: [PERFORMANCE.md § 기법 1](PERFORMANCE.md)
- **FAISS RAG + 디스크 캐싱**: 벡터 인덱스를 한 번 빌드하고 디스크에 저장. 이후 요청은 캐시에서 로드한다.
- **Scope Consistency Guard**: LLM 판사가 검색된 근거가 사용자 질문에 실제로 맞는지 점수를 매긴다. 무관한 문단은 제거하고, 아무것도 남지 않으면 웹 검색으로 폴백한다. → 판단 근거: [DECISIONS.md § 3](DECISIONS.md)
- **Offer Gate**: 초기 응답 후 사용자에게 아침/저녁 루틴, 제품 추천, 또는 다른 주제로 넘어갈지 선택지를 제공한다.
- **Conversation Router**: 동일 세션 내 후속 질문을 위한 순환 흐름.

→ `skeleton/agents/skincare/graph.py`, `diagrams/skincare_pipeline.md` 참조

### Skincare RAG 파이프라인

FAISS 기반 검색-생성 파이프라인. 7개 모듈로 구성:

```
loaders → splitter → embeddings → index_faiss (디스크 캐싱)
    → retriever → llm_helpers (쿼리확장 + 문서필터링)
    → chain (캐싱된 검색 + LLM 응답 생성)
    → cache (cross-user RAG 결과 캐싱)
```

<details>
<summary>주요 설계 결정</summary>

- **디스크 캐싱된 FAISS 인덱스**: 서버 재시작 시 임베딩 재계산 없이 로드 (`load_local`)
- **LLM 쿼리 확장**: 슬롯 정보로 검색 키워드 8~14개 생성 + `lru_cache`로 동일 조합 재사용
- **LLM 문서 필터링/재랭킹**: 검색된 문서 중 primary_concern에 무관한 것 제거, 관련도 순 재정렬
- **RAG 캐시**: concern + skin_type + primary_concern 조합으로 키 생성. session_id 미포함 → cross-user 캐시 히트. → 캐시 설계: [PERFORMANCE.md § 기법 6](PERFORMANCE.md)

</details>

→ `skeleton/agents/skincare/rag/` 참조

### Reco Agent — LLM Planner + 벡터 검색

제품 추천 파이프라인:

```
슬롯 추출 → [1-2개 질문으로 보완] → LLM 플랜 생성 → 벡터 검색 + 다차원 스코어링 → 응답 생성
```

<details>
<summary>2가지 검색 경로 상세</summary>

- **벡터 검색** (`ProductVectorSearch`): 사전 계산된 임베딩(NPZ) + FAISS IndexFlatIP로 코사인 유사도 검색. 카테고리/가격 후처리 필터.
- **LLM Planner** (`ProductSearchServiceLLMPlanner`): LLM이 검색 플랜 JSON을 생성하고, DataFrame 위에서 성분/키워드/카테고리/리뷰를 다차원 스코어링. content score(60%) + popularity(40%) 가중합.

보완 질문은 한번에 최대 2개까지 묶어서 물어 추가 질의 횟수를 최소화한다.
사용자가 카테고리를 지정하지 않은 경우 "any category" 모드로 전체 검색을 수행한다.

</details>

→ `skeleton/agents/reco/vector_search.py`, `skeleton/agents/reco/tools_llm_search.py` 참조

### AS Agent — 선형 슬롯 수집

A/S 접수(보증, 기기 불량)를 순차적 파이프라인으로 처리:

```
ingest → extract → decide → [ask_product → ask_symptom → ask_customer_info
                             → ask_confirm → process_confirm] → complete
```

<details>
<summary>처리 구조</summary>

총 12개 노드. `node_decide`가 중앙 라우터 역할을 하며, stage + 슬롯 충족 여부를 보고 다음 질문을 결정한다. 모든 슬롯이 채워지고 확인까지 받으면 DB에 접수를 기록한다.

LLM 호출 비중이 낮고 deterministic flow 비율이 높다 — 추출은 경량 로직이며, 슬롯이 모이면 흐름은 결정적이다.

</details>

→ `skeleton/agents/as_service/graph.py` 참조

### CS Agent — 이슈 분류 + RAG + 외부 API

조건부 엣지 7개, 스테이지 11개로 조건부 분기 수가 가장 많은 에이전트.
주문 조회, 환불, 제품 문의, 배송 추적 등을 처리한다.

```
parse_input → classify_issue → [confirm_product_brand]
           → check_handoff → collect_slots
           → [ask_question | query_external]
           → search_knowledge → generate_response → complete
```

<details>
<summary>주요 특징</summary>

- **이슈 분류**: LLM이 12개 이슈 유형 중 하나로 분류 (불량, 교환, 환불, 배송, 제품문의, 성분 등)
- **자사 브랜드 확인**: 보증/환불 요청 시 자사 제품인지 먼저 검증
- **외부 API 연동**: 주문관리 시스템에서 배송현황, 주문상세 조회 (회원은 user_id, 비회원은 주문번호)
- **RAG 검색**: ChromaDB 기반 제품 문서 + FAQ 지식베이스 벡터 검색. 제품명 한글/영문 양방향 매칭 + Unicode NFC 정규화.
- **도메인 전환 intent 감지**: 스킨케어 질문 → skincare agent, 추천 요청 → reco agent로 위임
- **응답 스타일 정책 적용**: 이슈 심각도에 따라 응답 스타일 변경 (공손 / 친근 / 공감형)

</details>

→ `skeleton/agents/cs/graph.py`, `skeleton/agents/cs/rag.py` 참조

---

## 3. Supervisor 패턴

멀티 intent 질의 (예: "내 피부 고민도 알려주고 제품도 추천해줘")를 처리:

```
supervisor_plan → supervisor_execute → supervisor_validate → supervisor_merge
```

<details>
<summary>4단계 처리 흐름</summary>

1. **Plan**: LLM이 필요한 에이전트를 식별하고 병렬 실행 가능 여부 판단
2. **Execute**: `asyncio.gather`로 에이전트 동시 실행
3. **Validate**: LLM이 모든 측면이 커버됐는지 확인; 부족하면 재시도 (최대 2회)
4. **Merge**: LLM이 3가지 전략 중 하나로 응답 통합:
   - `integrated` — 하나의 자연스러운 답변으로 엮기
   - `side_by_side` — 도메인별 섹션으로 나누기
   - `sequential` — 관련도 순서대로 나열

</details>

---

## 4. Infrastructure

### Redis 기반 세션 저장 + 캐시

세션 관리와 캐시를 운영 단순화를 위해 Redis로 통합하되, 용도별로 DB를 분리한다. → 캐시 키 설계와 cross-user 공유: [PERFORMANCE.md § 기법 6](PERFORMANCE.md) · 분리 판단: [DECISIONS.md § 2, 5](DECISIONS.md)

| 용도 | Redis DB | 키 패턴 | TTL |
|---|---|---|---|
| 세션 메타데이터 | db=1 | `session:{id}` | 90일 (접근 시 갱신) |
| OrchestratorState | db=1 | `state:{id}` | 세션과 동일 |
| LLM/라우팅 캐시 | db=0 | `router:{step}:{hash}` | 1시간 |
| 에이전트 응답 캐시 | db=0 | `agent:{name}:{hash}` | 1시간 |

<details>
<summary>구현 상세</summary>

**추상 인터페이스 분리**: `SessionStore`(세션)와 `CacheManager`(캐시) ABC를 정의하고, Redis 구현체(`RedisSessionStore`, `RedisCache`)를 주입한다. 테스트 환경에서 인메모리 구현으로 교체 가능.

**OrchestratorState 직렬화**: Pydantic `model_dump()` → JSON → `SETEX`. 에이전트 전환 시 이전 에이전트의 상태가 Redis에 유지되어 핸드오프 후에도 상태 연속성이 보장된다.

**캐시 키 설계**: `SHA256(args|sorted_kwargs)` — session_id를 포함하지 않아 cross-user 캐시 히트가 가능하다. 라우팅 결정과 에이전트 응답 모두 동일 키 생성 로직을 공유한다.

</details>

→ `skeleton/storage/session_store.py`, `skeleton/storage/redis_store.py`, `skeleton/cache/cache_manager.py`, `skeleton/cache/redis_cache.py` 참조

### ContextVar 트레이싱

요청마다 `PipelineTracer`를 생성하고 `ContextVar`에 바인딩한다.
콜스택 어디서든 `get_tracer()`로 스팬을 기록하거나, TTFT를 마킹하거나, 노드 경로를 남길 수 있다 — 전역 컨텍스트 기반으로 tracing 일관성을 유지한다.

<details>
<summary>사용 예시</summary>

```python
tracer = PipelineTracer(session_id="...")
token = set_tracer(tracer)
try:
    t = get_tracer()
    with t.span("evidence_retriever"):
        docs = faiss_index.similarity_search(query)
finally:
    reset_tracer(token)
    summary = tracer.finish()  # → TraceSummary (TTFT, E2E, spans, path)
```

</details>

### 노드별 메트릭

그래프의 모든 노드에 `with_node_metrics` / `with_node_metrics_async` 데코레이터가 걸려 있어 공통 데코레이터 레이어에서 기록한다:
- 실행 시간 (ms)
- LLM 호출 횟수 + 토큰 사용량
- 상태 변경 내역 (필드 레벨 diff)
- 에러

`MetricsStore`에 집계되어 세션별 또는 전체 통계 (TTFT p50/p95 포함)로 조회 가능하다.

### LLM 호출 계층

모든 에이전트의 LLM 호출은 2계층으로 표준화되어 있다:

**OpenAILLM** — OpenAI SDK 어댑터:
- 용도별 차등 타임아웃: `QUICK(15s)` / `DEFAULT(30s)` / `COMPLEX(60s)` / `STREAMING(120s)`
- 지수 백오프 재시도 (Timeout, RateLimitError, APIConnectionError 구분)
- tool_calls 정규화 + arguments JSON 파싱 옵션
- 호출별 usage/cost 로깅
- `astream()`: AsyncOpenAI 기반 토큰 단위 스트리밍

**LLMCallBuilder** — 통합 호출 빌더:
- 에이전트 코드 중복 ~80% 감소
- 공통 빌더 레이어에서 캐싱 처리: `MD5(model|system|user)` 키로 cross-session 히트
- Pydantic 자동 검증: `output_schema` 파라미터로 응답을 스키마에 매핑
- JSON 보정: 코드펜스 제거, 마지막 JSON 객체 추출
- 호출 통계: 모델별 토큰 사용량, 평균 레이턴시, 캐시 히트율

→ `skeleton/common/openai_client.py`, `skeleton/common/llm_caller.py` 참조

### Guardrail

- **핸드오프 guardrail**: §1 참조
- **실패 시 폴백**: 조건부 라우팅 실패 시 4-call 풀 라우팅으로 폴백
- **타입 안전성**: `ensure_response_text_is_string()`으로 ClarificationQuestion 리스트, dict, None 등을 안전한 문자열로 정규화 후 SSE 출력

---

## Code Map

| 모듈 | 핵심 파일 | 설명 |
|------|----------|------|
| **Orchestrator** | [schemas.py](skeleton/orchestrator/schemas.py) · [graph.py](skeleton/orchestrator/graph.py) · [llm_router.py](skeleton/orchestrator/llm_router.py) · [agent_adapters.py](skeleton/orchestrator/agent_adapters.py) | OrchestratorState, 11노드 그래프, 4-case 라우터, 어댑터 |
| **Skincare** | [graph.py](skeleton/agents/skincare/graph.py) · [slots.py](skeleton/agents/skincare/slots.py) · [rag/](skeleton/agents/skincare/rag/) | 9노드 파이프라인, quick-path 슬롯, FAISS RAG 7모듈 |
| **Reco** | [graph.py](skeleton/agents/reco/graph.py) · [vector_search.py](skeleton/agents/reco/vector_search.py) · [tools_llm_search.py](skeleton/agents/reco/tools_llm_search.py) | 추천 그래프, 벡터 검색, LLM Planner |
| **AS / CS** | [as/graph.py](skeleton/agents/as_service/graph.py) · [cs/graph.py](skeleton/agents/cs/graph.py) · [cs/rag.py](skeleton/agents/cs/rag.py) | A/S 12노드, CS 10노드 + ChromaDB RAG |
| **Services** | [chat_service.py](skeleton/services/chat_service.py) | SSE 스트리밍, 체크포인트 복구 |
| **Common** | [tracer.py](skeleton/common/tracer.py) · [metrics.py](skeleton/common/metrics.py) · [openai_client.py](skeleton/common/openai_client.py) · [llm_caller.py](skeleton/common/llm_caller.py) · [memory_cache.py](skeleton/common/memory_cache.py) | 트레이서, 메트릭, OpenAI 래퍼, 통합 LLM 빌더, 캐시 |
| **Storage / Cache** | [session_store.py](skeleton/storage/session_store.py) · [redis_store.py](skeleton/storage/redis_store.py) · [cache_manager.py](skeleton/cache/cache_manager.py) · [redis_cache.py](skeleton/cache/redis_cache.py) | 세션 ABC + Redis 구현, 캐시 ABC + Redis 구현 |
