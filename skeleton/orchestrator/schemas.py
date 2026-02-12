"""오케스트레이터 스키마 정의. 라우팅 판단 결과를 Pydantic 모델로 표현."""

from __future__ import annotations
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


AgentType = Literal["skincare", "reco", "as", "cs", "intent", "unknown"]


class IntentDecision(BaseModel):
    """LLM이 분류한 사용자 의도"""
    intent: Literal["skincare", "recommend", "as", "cs", "unknown"] = "unknown"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reason: str = ""
    keywords: List[str] = Field(default_factory=list)
    context_factors: List[str] = Field(default_factory=list)
    is_multi_intent: bool = False


class AgentDecision(BaseModel):
    """LLM이 선택한 담당 에이전트"""
    selected_agent: AgentType = "unknown"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reason: str = ""
    alternative_agents: List[AgentType] = Field(default_factory=list)
    requires_handoff: bool = False


class HandoffDecision(BaseModel):
    """에이전트 간 전환 필요 여부"""
    should_handoff: bool = False
    from_agent: Optional[AgentType] = None
    to_agent: Optional[AgentType] = None
    reason: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    transfer_data: Dict[str, Any] = Field(default_factory=dict)
    user_message: Optional[str] = None


class PendingHandoff(BaseModel):
    """사용자 확인 대기 중인 핸드오프"""
    from_agent: AgentType
    to_agent: AgentType
    reason: str
    confirmation_question: str
    detected_intent: str
    user_input: str


class ClarificationQuestion(BaseModel):
    """명확화 질문 (우선순위 + 선택지)"""
    question: str
    question_type: Literal["missing_slot", "ambiguous", "confirmation", "suggestion"] = "missing_slot"
    priority: int = Field(default=1, ge=1, le=5)
    suggested_answers: List[str] = Field(default_factory=list)
    slot_name: Optional[str] = None


class CompletenessDecision(BaseModel):
    """수집 정보 완성도 판단"""
    is_complete: bool = False
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    missing_info: List[str] = Field(default_factory=list)
    clarification_questions: List[ClarificationQuestion] = Field(default_factory=list)
    reason: str = ""
    can_proceed_anyway: bool = False
    assumptions: Dict[str, Any] = Field(default_factory=dict)
    collection_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    next_priority_slot: Optional[str] = None


class ConversationFlow(BaseModel):
    """대화 흐름 단계 제어"""
    current_phase: Literal[
        "greeting", "info_gathering", "clarifying", "processing",
        "confirming", "presenting", "follow_up", "closing",
    ] = "info_gathering"
    next_phase: Optional[str] = None
    can_skip_to_result: bool = False
    conversation_style: Literal["formal", "friendly", "professional"] = "friendly"
    strategy: Literal[
        "ask_all_upfront", "progressive_collection",
        "minimal_questions", "conversational",
    ] = "progressive_collection"


class NextStepDecision(BaseModel):
    """다음 처리 단계 결정"""
    next_action: Literal[
        "collect_info", "process", "handoff", "finalize",
        "escalate", "end", "clarify", "confirm", "suggest_alternative",
    ] = "collect_info"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reason: str = ""
    suggested_response: Optional[str] = None
    conversation_flow: Optional[ConversationFlow] = None
    fallback_action: Optional[str] = None
    retry_strategy: Optional[str] = None


# --- Multi-Agent Supervisor ---

class SupervisorPlan(BaseModel):
    """복합 질문 분석 — 어떤 에이전트들이 필요한지"""
    agents: List[str] = Field(default_factory=list)
    parallel: bool = True
    reasoning: str = ""
    is_complex: bool = False


class SupervisorValidation(BaseModel):
    """에이전트 응답 검증"""
    is_sufficient: bool = True
    retry_agents: List[str] = Field(default_factory=list)
    missing_aspects: List[str] = Field(default_factory=list)
    merge_strategy: Literal["integrated", "side_by_side", "sequential"] = "integrated"


# --- 통합 오케스트레이터 상태 ---

class OrchestratorState(BaseModel):
    """그래프를 통과하는 중앙 상태 객체"""

    # 세션
    session_id: str = Field(default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    language: str = "ko"

    # 사용자 입력
    user_text: str = ""
    last_user_text: Optional[str] = None

    # 대화 히스토리
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    conversation_turns: int = 0

    # 메모리 (시맨틱 검색 + 유저 프로필)
    user_profile: Optional[Dict[str, Any]] = None
    relevant_memories: List[Dict[str, Any]] = Field(default_factory=list)
    is_returning_user: bool = False
    personalized_greeting: Optional[str] = None

    # LLM 판단 결과
    intent_decision: Optional[IntentDecision] = None
    agent_decision: Optional[AgentDecision] = None
    handoff_decision: Optional[HandoffDecision] = None
    completeness_decision: Optional[CompletenessDecision] = None
    next_step_decision: Optional[NextStepDecision] = None
    pending_handoff: Optional[PendingHandoff] = None

    # 핸드오프 루프 방지
    handoff_chain: List[str] = Field(default_factory=list)
    handoff_count: int = 0
    pending_handoff_created_at: Optional[datetime] = None

    # 에이전트 라우팅
    current_agent: AgentType = "intent"
    previous_agent: Optional[AgentType] = None

    # 에이전트별 상태 + 공유 컨텍스트
    agent_states: Dict[AgentType, Dict[str, Any]] = Field(default_factory=dict)
    shared_context: Dict[str, Any] = Field(default_factory=dict)

    # 응답
    response_text: str = ""
    response_metadata: Dict[str, Any] = Field(default_factory=dict)

    # 플래그
    needs_user_input: bool = False
    is_complete: bool = False
    is_escalated: bool = False

    # 에러 처리
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    # Supervisor
    supervisor_plan: Optional[SupervisorPlan] = None
    supervisor_validation: Optional[SupervisorValidation] = None
    agent_results: Dict[str, str] = Field(default_factory=dict)
    supervisor_retry_count: int = 0

    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)


class LLMResponse(BaseModel):
    """LLM 응답 표준화 래퍼"""
    raw_content: str
    parsed_data: Dict[str, Any] = Field(default_factory=dict)
    parse_success: bool = True
    parse_error: Optional[str] = None


# --- 라우터 헬퍼 스키마 (feature flag 기반) ---

class TopicChangeDecision(BaseModel):
    """주제 급변 감지"""
    topic_changed: bool = False
    new_topic: Optional[Literal["as", "recommend", "skincare", "cs"]] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reason: str = ""


class HandoffResponseAnalysis(BaseModel):
    """핸드오프 제안에 대한 사용자 응답 분석"""
    user_choice: Literal["accept", "reject", "both", "unclear"] = "unclear"
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reason: str = ""
    suggested_action: Literal["proceed_handoff", "stay_current", "ask_again"] = "stay_current"


class DomainMatchDecision(BaseModel):
    """현재 입력이 활성 에이전트 도메인에 맞는지"""
    domain_match: bool = True
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reason: str = ""
    should_full_route: bool = False
