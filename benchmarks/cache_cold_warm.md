# Cold-path vs Warm-path 캐시 벤치마크

## 테스트 환경
- **서버**: FastAPI + LangGraph 멀티 에이전트 오케스트레이터 (로컬, 단일 프로세스)
- **모델**: gpt-4o / gpt-4o-mini
- **방법**: streaming=true, 워밍업 3회 제외, 5회 평균
- **캐시 초기화**: `POST /debug/cache/clear` — 4개 인메모리 캐시 레이어 전체 초기화
  - MemoryCache (LLM 라우팅/응답), RAGCache (검색), SimpleCache (함수 레벨), LRU (쿼리 확장)

---

## 1. 레이턴시 비교 (5회 평균, ms)

| Agent | 시나리오 | Cold TTFT | Warm TTFT | Cold E2E | Warm E2E |
|:---:|---|---:|---:|---:|---:|
| Skincare | 모공 고민 (슬롯+RAG) | 5,828 | 5,100 | 7,735 | 7,121 |
| Reco | 제품 추천 | 16,825 | 1,928 | 27,743 | 12,238 |
| Skincare | 정보성 질문 (how-to) | 15,136 | 15,406 | 18,750 | 19,130 |
| AS | 디바이스 전원 문제 | 5,431 | 3,687 | 9,518 | 7,383 |
| CS | 제품 사용 문의 | 20,838 | 905 | 29,957 | 10,129 |
| Supervisor | Skincare + Reco 복합 질의 | 42,704 | 1,453 | 55,971 | 12,581 |

## 2. 캐시 효과 (Cold → Warm 개선율)

| Agent | 시나리오 | TTFT 개선율 | E2E 개선율 | 캐시 히트율 |
|:---:|---|---:|---:|---:|
| **CS** | 제품 사용 문의 | **-95.7%** | **-66.2%** | 80.0% |
| **Reco** | 제품 추천 | **-88.5%** | **-55.9%** | 66.7% |
| **AS** | 디바이스 전원 문제 | **-32.1%** | **-22.4%** | 60.0% |
| Skincare | 모공 고민 | -12.5% | -7.9% | 33.3% |
| Skincare | 정보성 질문 | +1.8% | +2.0% | 45.0% |
| **Supervisor** | Skincare + Reco 복합 | **-96.6%** | **-77.5%** | 66.7% |

## 3. 분석

**Cold-path** = 캐시 없음, 순수 처리 비용.
**Warm-path** = 캐시 활성, 운영 환경과 유사한 성능.

| 패턴 | 설명 |
|---|---|
| **CS / Reco** | MemoryCache 히트로 LLM 라우팅 + 응답 체인 전체를 건너뜀 → TTFT **1초 미만** |
| **AS** | 라우터 캐시 히트로 의도 분류 호출 절감 → TTFT 32% 감소 |
| **Skincare (모공)** | 턴마다 슬롯이 변경되어 부분적 캐시 미스 발생 → 소폭 개선 |
| **Skincare (how-to)** | RAG 캐시 히트(45%)이지만 하류 LLM 호출이 지배적 → 순 개선 없음 |
| **Supervisor** | Cold path가 가장 느림(~56초) — 계획 수립 + 이중 에이전트 실행 때문. Warm path에서 MemoryCache 히트로 라우팅 건너뜀 → TTFT **1.5초 미만**, E2E **-77.5%** |

## 4. 캐시 키 설계 (Cross-User 공유)

```
memory_cache : MD5(model | system_prompt | user_prompt)
rag_cache    : MD5(concern | skin_type | primary_concern)
simple_cache : MD5(JSON(args, kwargs))
lru_cache    : tuple(primary_concern, skin_type, concerns_key, avoid_key)
```

> 캐시 키에 **session_id를 의도적으로 제외** — 다른 사용자의 동일 질의가 캐시 엔트리를 공유한다.
> CS/Reco의 warm TTFT가 1초 미만으로 떨어지는 이유: 첫 번째 사용자가 캐시를 프라이밍하면 이후 사용자 전원이 혜택을 받는다.
