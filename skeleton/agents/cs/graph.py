"""CS(고객서비스) 에이전트 이슈 분류 + RAG + 외부 API 그래프."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


class CSStage(str, Enum):
    INITIAL = "initial"
    CLASSIFY_ISSUE = "classify_issue"
    CONFIRM_PRODUCT_BRAND = "confirm_product_brand"
    COLLECT_INFO = "collect_info"
    CHECK_HANDOFF = "check_handoff"
    QUERY_EXTERNAL = "query_external"
    SEARCH_KNOWLEDGE = "search_knowledge"
    GENERATE_RESPONSE = "generate_response"
    CONFIRM = "confirm"
    COMPLETE = "complete"
    WAIT_USER = "wait_user"


class IssueType(str, Enum):
    DEFECT = "defect"
    EXCHANGE = "exchange"
    REFUND = "refund"
    DELIVERY_TRACKING = "delivery_tracking"
    DELIVERY_INQUIRY = "delivery_inquiry"
    PRODUCT_INFO = "product_info"
    USAGE = "usage"
    INGREDIENTS = "ingredients"
    PREGNANCY_SAFE = "pregnancy_safe"
    GENERAL = "general"
    ESCALATION = "escalation"
    UNKNOWN = "unknown"


class ToneStyle(str, Enum):
    FORMAL = "formal"
    FRIENDLY = "friendly"
    PROFESSIONAL = "professional"
    EMPATHETIC = "empathetic"


class CSSlots(BaseModel):
    """이슈/주문 관련 추출 정보."""
    issue_type: Optional[IssueType] = None
    order_number: Optional[str] = None
    product_name: Optional[str] = None
    issue_description: Optional[str] = None
    customer_contact: Optional[str] = None
    product_inquiry: Optional[str] = None
    inquiry_context: Optional[str] = None
    purchase_date: Optional[str] = None
    delivery_address: Optional[str] = None
    refund_reason: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    is_company_product: Optional[bool] = None


class UserContext(BaseModel):
    """회원/비회원 식별 정보."""
    is_member: bool = False
    user_id: Optional[str] = None
    name: Optional[str] = None


class CSState(BaseModel):
    """CS 에이전트 내부 상태 (체크포인트 유지)."""
    user_text: str = ""
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    user_context: UserContext = Field(default_factory=UserContext)
    slots: CSSlots = Field(default_factory=CSSlots)
    stage: CSStage = CSStage.INITIAL
    need_more_info: bool = False
    missing_slots: List[str] = Field(default_factory=list)
    order_info: Optional[Dict[str, Any]] = None
    order_list: Optional[List[Dict[str, Any]]] = None
    rag_results: List[str] = Field(default_factory=list)
    message_to_user: str = ""
    tone_style: ToneStyle = ToneStyle.FRIENDLY
    should_handoff: bool = False
    handoff_target: Optional[str] = None  # "reco", "skincare", "as"
    is_resolved: bool = False
    resolution_type: Optional[str] = None  # answered, escalated, handoff, pending, error


# ---- 노드 함수 ----

def node_parse_input(state: CSState) -> CSState:
    """유저 입력 파싱, 복귀 컨텍스트 감지, 단계 초기화."""
    ...


def node_classify_issue(state: CSState, llm) -> CSState:
    """LLM 기반 이슈 유형 분류."""
    ...


def node_confirm_product_brand(state: CSState, llm) -> CSState:
    """언급된 제품이 자사 브랜드인지 확인."""
    ...


def node_check_handoff(state: CSState) -> CSState:
    """다른 에이전트로 핸드오프 필요 여부 판단."""
    ...


def node_collect_slots(state: CSState, llm) -> CSState:
    """이슈 유형별 LLM 슬롯 추출."""
    ...


def node_ask_question(state: CSState, llm) -> CSState:
    """부족한 필수 슬롯에 대한 추가 질문 생성."""
    ...


def node_query_external(state: CSState) -> CSState:
    """외부 API 조회 (주문관리, 배송추적). 회원은 user_id, 비회원은 주문번호."""
    ...


def node_search_knowledge(state: CSState, rag_service) -> CSState:
    """제품 문서 및 FAQ 지식베이스 RAG 검색."""
    ...


def node_generate_response(state: CSState, llm) -> CSState:
    """주문 데이터 + RAG 결과 + 대화 컨텍스트로 최종 응답 생성."""
    ...


def node_complete(state: CSState) -> CSState:
    """대화 완료 처리 및 해결 유형 기록."""
    ...


# ---- 조건부 엣지 함수 ----

def route_after_parse_input(state: CSState) -> str:
    """classify_issue / collect_slots / confirm_product_brand로 분기."""
    ...


def route_after_classification(state: CSState) -> str:
    """check_handoff / confirm_product_brand / collect_slots로 분기."""
    ...


def route_after_product_brand_confirm(state: CSState) -> str:
    """collect_slots / check_handoff / END 분기."""
    ...


def route_after_handoff_check(state: CSState) -> str:
    """핸드오프면 complete, 아니면 collect_slots."""
    ...


def route_after_slot_collection(state: CSState) -> str:
    """정보 부족하면 ask_question, 충분하면 query_external."""
    ...


def route_after_question(state: CSState) -> str:
    """유저 대기(END) 또는 query_external."""
    ...


def route_after_query_external(state: CSState) -> str:
    """아직 부족하면 ask_question, 충분하면 search_knowledge."""
    ...


# ---- 그래프 빌더 ----

def build_cs_graph(
    llm=None,
    rag_service=None,
    enable_rag: bool = True,
    checkpointer=None,
):
    """CS 에이전트 StateGraph 빌드 및 컴파일."""
    graph = StateGraph(CSState)

    # graph.add_node("parse_input", node_parse_input)
    # graph.add_node("classify_issue", ...)
    # graph.add_node("confirm_product_brand", ...)
    # graph.add_node("check_handoff", node_check_handoff)
    # graph.add_node("collect_slots", ...)
    # graph.add_node("ask_question", ...)
    # graph.add_node("query_external", node_query_external)
    # graph.add_node("search_knowledge", ...)
    # graph.add_node("generate_response", ...)
    # graph.add_node("complete", node_complete)

    # graph.set_entry_point("parse_input")
    # graph.add_conditional_edges("parse_input", route_after_parse_input, {...})
    # graph.add_conditional_edges("classify_issue", route_after_classification, {...})
    # graph.add_conditional_edges("confirm_product_brand", route_after_product_brand_confirm, {...})
    # graph.add_conditional_edges("check_handoff", route_after_handoff_check, {...})
    # graph.add_conditional_edges("collect_slots", route_after_slot_collection, {...})
    # graph.add_conditional_edges("ask_question", route_after_question, {...})
    # graph.add_conditional_edges("query_external", route_after_query_external, {...})
    # graph.add_edge("search_knowledge", "generate_response")
    # graph.add_edge("generate_response", "complete")
    # graph.add_edge("complete", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
