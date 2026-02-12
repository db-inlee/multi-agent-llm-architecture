# Architectural Decisions

## TL;DR

- 4-case 분기로 턴당 LLM 호출 5회 → 0-2회: 대화 상태 기반 최소 호출 전략
- 캐시 키에서 session_id 제외: cross-user 캐시 히트로 warm-path TTFT -95.7%
- Scope Guard 추가: faithfulness 0.7-1.0 → 평균 0.96 (n=20)
- PendingHandoff: 즉시 전환 대신 확인 후 전환으로 상담 연속성 보장
- 체크포인트 에이전트별 분리: 핸드오프 시 상태 충돌 제거

각 결정의 근거와 트레이드오프. 구현 상세는 [ARCHITECTURE.md](ARCHITECTURE.md), 성능 수치는 [PERFORMANCE.md](PERFORMANCE.md) 참조.

---

## 1. 4-case 라우팅으로 LLM 호출 최소화

**관찰**: 프로파일링 결과 멀티턴 세션의 60%가 같은 에이전트 연속 턴이었다.
에이전트가 대기 상태(질문 후 답변 대기)면 다음 메시지는 그 답변일 확률이 높은 것으로 관찰되었다.

**판단**: 매 턴 5회 LLM 호출을 돌리는 대신, 대화 상태를 보고 필요한 호출만 수행하는 4-case 분기를 설계했다. 불필요한 LLM 호출을 줄여 latency와 API 비용을 동시에 절감하는 구조다. 대부분의 턴에서 LLM 0~2회로 충분하다.

**결과**: benchmark 기준 턴당 LLM 호출 5회 → 0~2회. 첫 턴 라우팅 지연 ~40% 감소.

→ 분기 테이블: [ARCHITECTURE.md § 4-Case 조건부 라우팅](ARCHITECTURE.md) · 최적화 기법: [PERFORMANCE.md § 기법 3~4](PERFORMANCE.md)

---

## 2. 캐시 키에서 session_id 제외

**관찰**: "건성 피부 보습제 추천" 같은 질문은 사용자가 달라도 라우팅 판단과 RAG 결과가 동일하다. session_id를 캐시 키에 넣으면 모든 사용자가 cold start를 겪는다.

**판단**: 캐시 키를 `MD5(model | system_prompt | user_prompt)`로 구성하고 session_id를 제외했다. 라우팅 프롬프트와 검색 질의 패턴이 사용자 간 거의 동일하다는 운영 로그 관찰을 기반으로 설계했다. 사용자 A의 결과를 사용자 B가 재사용한다.

**트레이드오프**: 사용자별 맞춤 응답이 필요한 경우 캐시 미스가 발생할 수 있지만, 라우팅 판단과 RAG 검색은 사용자 무관하므로 문제없다.

**결과**: benchmark 기준 warm-path CS TTFT **20.8초 → 0.9초** (-95.7%).

→ 4-layer 캐시 설계: [PERFORMANCE.md § 기법 6](PERFORMANCE.md) · Redis 키 구조: [ARCHITECTURE.md § Infrastructure](ARCHITECTURE.md)

---

## 3. Scope Guard로 hallucination 발생 확률 감소

**관찰**: FAISS embedding 유사도가 높다고 실제로 관련 있는 건 아니다. "여드름" 질문에 "주름" 문서가 높은 유사도로 검색되는 경우가 있었다.

**판단**: 검색과 생성 사이에 LLM 판정 단계를 추가했다. 추가 LLM 호출 1회의 latency 비용을 hallucination 발생 확률 감소와 맞바꿨으며, 운영 안정성 측면에서 합리적인 trade-off로 판단했다.

**결과**: 테스트 시나리오 기준 RAGAS faithfulness **0.7-1.0, 평균 0.96** (n=20).

→ 파이프라인 위치: [ARCHITECTURE.md § Skincare Agent](ARCHITECTURE.md)

---

## 4. PendingHandoff — 확인 후 전환

**관찰**: "추천해줘"가 에이전트 전환 의도가 아니라 가벼운 언급인 경우가 많았다. 즉시 전환하면 진행 중인 상담이 끊긴다.

**판단**: intent 변경 감지 시 바로 전환하지 않고, 사용자에게 확인 질문을 먼저 던진다. 확인 후에만 전환한다. 전환 반복으로 인한 루프를 방지하기 위해 전환 횟수 제한(3회) 후 CS로 fallback. 상담 연속성과 운영 안정성을 동시에 확보하는 구조다.

**결과**: 운영 로그 기준 불필요한 핸드오프 제거, 상담 연속성 유지 확인.

→ 안전장치 상세: [ARCHITECTURE.md § 핸드오프 Guardrail](ARCHITECTURE.md)

---

## 5. 체크포인트 에이전트별 분리

**관찰**: 단일 공유 체크포인트에서 agent A → B 전환 시 B가 공유 키를 덮어쓰면서 A의 슬롯에 상태 충돌이 발생했다.

**판단**: Redis 키 네임스페이스를 에이전트별로 분리하고(db=0 캐시 / db=1 세션), 오케스트레이터는 얇은 패스스루로만 사용한다. 상태 일관성을 보장하기 위한 에이전트 간 격리 구조다.

**결과**: 테스트 시나리오 기준 핸드오프 후에도 이전 에이전트의 슬롯 보존 확인.

→ Redis 키 구조: [ARCHITECTURE.md § Infrastructure](ARCHITECTURE.md)
