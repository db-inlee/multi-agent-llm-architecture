"""스킨케어 에이전트 9노드 StateGraph 정의."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import logging

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END

logger = logging.getLogger(__name__)


# ---- 상태 스키마 ----

class Evidence(BaseModel):
    """RAG/웹 검색 근거."""
    snippet: str
    source: Optional[str] = None
    kind: Optional[str] = None  # "rag" | "web"


class JudgeScores(BaseModel):
    """스코프 일관성 평가 점수."""
    concern_consistency: float = 0.0
    factuality: float = 0.0
    safety: float = 0.0
    clarity: float = 0.0


class JudgeResult(BaseModel):
    """스코프 일관성 가드 판정 결과."""
    decision: str = "pass"  # pass | rewrite | reject | needs_web
    scores: JudgeScores = Field(default_factory=JudgeScores)
    reasons: List[str] = Field(default_factory=list)
    rewrite_hints: List[str] = Field(default_factory=list)


class SkincareState(BaseModel):
    """스킨케어 에이전트 내부 상태 (체크포인트 유지)."""

    # 입력/슬롯
    skin_type: Optional[str] = None
    concerns: List[str] = Field(default_factory=list)
    ingredient_avoid: List[str] = Field(default_factory=list)
    budget: Optional[int] = None

    # 동적 매핑
    original_user_terms: List[str] = Field(default_factory=list)
    method_query: Optional[str] = None
    is_how_to: bool = False
    extracted_keywords: List[str] = Field(default_factory=list)

    # LLM 질문 타입 분류
    question_type: Optional[str] = None  # informational | recommendation | consultation
    skip_slot_collection: bool = False
    ingredient_query: bool = False
    extracted_ingredients: List[str] = Field(default_factory=list)

    # LLM 스코프
    primary_concern: Optional[str] = None
    deferred_concerns: List[str] = Field(default_factory=list)

    # 대화 제어
    wants_routine: Optional[bool] = None
    need_more_info: bool = False
    conversation_stage: Optional[str] = None  # empathize | clarify | advise | confirm | offer

    # 응답
    answer: str = ""
    evidence: List[Evidence] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    solution_summary: str = ""
    solution_struct: Dict[str, Any] = Field(default_factory=dict)

    # Judge
    judge_solution: Optional[JudgeResult] = None
    needs_web: bool = False

    # 라우팅
    intent: str = "skincare"
    handoff: Optional[str] = None

    # 다국어
    language: str = "ko"

    # Clarify
    ask_list: List[Dict[str, Any]] = Field(default_factory=list)

    # 대화 이력
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    last_user_intent: Optional[str] = None
    follow_up_questions: List[str] = Field(default_factory=list)

    # 발화 히스토리
    utterance_history: List[str] = Field(default_factory=list)
    last_utterance: str = ""

    # 순환 대화 방지
    conversation_turns: int = 0
    previous_answers: List[str] = Field(default_factory=list)
    follow_up_mode: bool = False
    current_topic: Optional[str] = None

    # 슬롯 수집 플래그
    asked_ingredient_avoid: bool = False

    # 다단계 상담
    last_user_text: str = ""
    information_sufficiency_score: float = 0.0
    probe_context: Dict[str, Any] = Field(default_factory=dict)

    # 피부 타입 간접 질문
    asked_skin_type_directly: bool = False
    asked_skin_type_indirectly: bool = False
    last_indirect_question: str = ""

    # ReAct 패턴
    react_steps: List[Dict[str, Any]] = Field(default_factory=list)
    react_iteration: int = 0
    react_goal_achieved: bool = False


# ---- 노드 함수 ----

def slot_collector(state: SkincareState) -> SkincareState:
    """필수 슬롯(고민, 피부타입) 수집. 정규식 우선, 실패 시 LLM 추출."""
    ...


def symptom_probe(state: SkincareState) -> SkincareState:
    """정보 충분도 체크 후 부족하면 추가 질문. 정보성 질문은 스킵."""
    ...


def evidence_retriever(state: SkincareState) -> SkincareState:
    """FAISS 벡터 검색으로 스킨케어 지식 조회. 고민+피부타입 기준 캐싱."""
    ...


def scope_consistency_guard(state: SkincareState) -> SkincareState:
    """LLM이 솔루션 적합도 평가, 주제 이탈 구간 제거. 부족하면 웹 폴백."""
    ...


def web_fallback(state: SkincareState) -> SkincareState:
    """RAG 근거 부족 시 Tavily 웹 검색으로 보완 답변 생성."""
    ...


def conversational_response(state: SkincareState) -> SkincareState:
    """공감->답변->조언->제안 패턴으로 응답 생성. 긴급도 분석 포함."""
    ...


def offer_gate(state: SkincareState) -> SkincareState:
    """루틴 요청/제품 문의/거절 중 유저 선택 대기."""
    ...


def routine_synthesizer(state: SkincareState) -> SkincareState:
    """RAG 근거 기반 AM/PM 스킨케어 루틴 생성."""
    ...


def finalize(state: SkincareState) -> SkincareState:
    """최종 답변 포맷팅, 안전 경고 및 출처 첨부."""
    ...


def conversation_router(state: SkincareState) -> SkincareState:
    """멀티턴 후속 인텐트 분류 후 적절한 노드로 재라우팅."""
    ...


# ---- 조건부 엣지 함수 ----

def after_collect(state: SkincareState) -> str:
    """slot_collector 후 라우팅: 후속질문/핸드오프/슬롯부족/준비완료."""
    ...


def after_probe(state: SkincareState) -> str:
    """추가정보 필요하면 END, 아니면 evidence_retriever로."""
    ...


def judge_route(state: SkincareState) -> str:
    """핸드오프/웹폴백/통과 분기."""
    ...


def after_web(state: SkincareState) -> str:
    """핸드오프면 END, 아니면 conversational_response로."""
    ...


def offer_next(state: SkincareState) -> str:
    """루틴 원함 -> routine_synthesizer, 거절 -> finalize, 미응답 -> END."""
    ...


def after_finalize(state: SkincareState) -> str:
    """최대 턴 초과면 END, 아니면 후속 대기."""
    ...


def route_followup(state: SkincareState) -> str:
    """conversation_stage에 따라 clarify/advise/offer/end로 분기."""
    ...


# ---- 그래프 빌더 ----

def build_graph(checkpointer=None):
    """스킨케어 StateGraph 빌드 및 컴파일."""
    graph = StateGraph(SkincareState)

    # -- 노드 등록 --
    # graph.add_node("slot_collector", slot_collector)
    # graph.add_node("symptom_probe", symptom_probe)
    # graph.add_node("evidence_retriever", evidence_retriever)
    # graph.add_node("scope_consistency_guard", scope_consistency_guard)
    # graph.add_node("web_fallback", web_fallback)
    # graph.add_node("conversational_response", conversational_response)
    # graph.add_node("offer_gate", offer_gate)
    # graph.add_node("routine_synthesizer", routine_synthesizer)
    # graph.add_node("finalize", finalize)
    # graph.add_node("conversation_router", conversation_router)

    # -- 진입점 --
    graph.set_entry_point("slot_collector")

    # -- 조건부 엣지 --
    # graph.add_conditional_edges("slot_collector", after_collect, {...})
    # graph.add_conditional_edges("symptom_probe", after_probe, {...})
    # graph.add_edge("evidence_retriever", "scope_consistency_guard")
    # graph.add_conditional_edges("scope_consistency_guard", judge_route, {...})
    # graph.add_conditional_edges("web_fallback", after_web, {...})
    # graph.add_edge("conversational_response", "offer_gate")
    # graph.add_conditional_edges("offer_gate", offer_next, {...})
    # graph.add_edge("routine_synthesizer", "finalize")
    # graph.add_conditional_edges("finalize", after_finalize, {...})
    # graph.add_conditional_edges("conversation_router", route_followup, {...})

    return graph.compile(checkpointer=checkpointer)
