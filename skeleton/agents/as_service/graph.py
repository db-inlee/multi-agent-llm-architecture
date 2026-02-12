"""AS(애프터서비스) 에이전트 순차 슬롯 수집 그래프."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
import logging

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


class ASSlots(BaseModel):
    """AS 접수 과정에서 수집하는 정보."""
    product_name: Optional[str] = None
    symptom_summary: Optional[str] = None
    symptom_full: Optional[str] = None
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None


class ASState(BaseModel):
    """AS 에이전트 내부 상태 (체크포인트 유지)."""
    user_text: str = ""
    slots: ASSlots = Field(default_factory=ASSlots)
    stage: str = "start"
    # 단계: start, wait_product, wait_symptom, wait_customer_info,
    #       wait_confirm, confirmed, complete, finalize
    message_to_user: Optional[str] = None
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    thread_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    last_user_text: Optional[str] = None
    turn_count: int = 0


# ---- 노드 함수 ----

def node_ingest(state: ASState) -> ASState:
    """유저 메시지 이력 추가, 턴 카운트 증가."""
    ...


def node_extract(state: ASState) -> ASState:
    """단계에 따라 제품명/증상/고객정보 LLM 추출."""
    ...


def node_decide(state: ASState) -> str:
    """단계와 슬롯 채움 상태에 따른 조건부 라우팅."""
    ...


def node_ask_product(state: ASState) -> ASState:
    """문제 제품 문의."""
    ...


def node_ask_symptom(state: ASState) -> ASState:
    """증상/불량 설명 요청."""
    ...


def node_ask_customer_info(state: ASState) -> ASState:
    """수거/보증 서비스용 이름, 연락처, 주소 요청."""
    ...


def node_apply_product_reply(state: ASState) -> ASState:
    """유저의 제품명 응답을 슬롯에 반영."""
    ...


def node_apply_symptom_reply(state: ASState) -> ASState:
    """유저의 증상 설명을 슬롯에 반영."""
    ...


def node_apply_customer_reply(state: ASState) -> ASState:
    """유저의 연락처 정보를 슬롯에 반영."""
    ...


def node_ask_confirm(state: ASState) -> ASState:
    """수집 정보 요약 후 확인 요청."""
    ...


def node_process_confirm(state: ASState) -> ASState:
    """유저의 확인/거부 응답 처리."""
    ...


def node_complete(state: ASState) -> ASState:
    """AS 접수 DB 저장 및 완료 메시지 생성."""
    ...


def node_finalize(state: ASState) -> ASState:
    """오케스트레이터 통합용 최종 노드."""
    ...


# ---- 그래프 빌더 ----

def build_graph(checkpointer=None):
    """AS 에이전트 StateGraph 빌드 및 컴파일."""
    graph = StateGraph(ASState)

    # graph.add_node("ingest", node_ingest)
    # graph.add_node("extract", node_extract)
    # graph.add_node("ask_product", node_ask_product)
    # graph.add_node("ask_symptom", node_ask_symptom)
    # graph.add_node("ask_customer_info", node_ask_customer_info)
    # graph.add_node("apply_product_reply", node_apply_product_reply)
    # graph.add_node("apply_symptom_reply", node_apply_symptom_reply)
    # graph.add_node("apply_customer_reply", node_apply_customer_reply)
    # graph.add_node("ask_confirm", node_ask_confirm)
    # graph.add_node("process_confirm", node_process_confirm)
    # graph.add_node("complete", node_complete)

    # graph.set_entry_point("ingest")
    # graph.add_edge("ingest", "extract")
    # graph.add_conditional_edges("extract", node_decide, {...})
    # graph.add_edge("ask_product", END)        # 유저 응답 대기
    # graph.add_edge("ask_symptom", END)         # 유저 응답 대기
    # graph.add_edge("ask_customer_info", END)   # 유저 응답 대기
    # graph.add_edge("ask_confirm", END)         # 유저 응답 대기
    # graph.add_edge("complete", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
