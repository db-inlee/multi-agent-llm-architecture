"""제품 추천 에이전트 LangGraph 상태 머신."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import logging

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

ESSENTIAL = ("skin_type", "concerns")


class SessionState(BaseModel):
    """추천 에이전트 내부 상태 (체크포인트 유지)."""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    slots: Dict[str, Any] = Field(default_factory=dict)
    asked: List[str] = Field(default_factory=list)
    mode: str = "ASK_OR_SEARCH"
    pending_questions: List[Dict[str, Any]] = Field(default_factory=list)
    offtopic_count: int = 0
    result_text: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    status: str = "RUNNING"  # RUNNING | NEED_MORE_INFO | ANSWER | ESCALATE_INTENT
    last_user_text: Optional[str] = None
    category_suggestions: Optional[List[str]] = None
    conversation_history: Optional[List[Dict[str, str]]] = Field(default=None)


# ---- 노드 함수 ----

def node_extract(state: SessionState) -> SessionState:
    """LLM 슬롯 추출 + 검증."""
    ...


def node_clarify(state: SessionState) -> SessionState:
    """보완 질문 1~2개 묶어서 유저에게 전달."""
    ...


def node_search(state: SessionState) -> SessionState:
    """상품 카탈로그 검색 + 필터 적용."""
    ...


def node_rerank(state: SessionState) -> SessionState:
    """LLM으로 검색 결과를 유저 니즈 적합도 기준 재정렬."""
    ...


def node_answer(state: SessionState) -> SessionState:
    """최종 추천 응답 생성."""
    ...


# ---- 조건부 엣지 ----

def should_continue(state: SessionState) -> str:
    """status에 따라 clarify/search/END/extract로 분기."""
    ...


# ---- 그래프 빌더 ----

def build_reco_graph(checkpointer=None):
    """추천 에이전트 StateGraph 빌드 및 컴파일."""
    graph = StateGraph(SessionState)

    # graph.add_node("extract", node_extract)
    # graph.add_node("clarify", node_clarify)
    # graph.add_node("search", node_search)
    # graph.add_node("rerank", node_rerank)
    # graph.add_node("answer", node_answer)

    # graph.set_entry_point("extract")
    # graph.add_conditional_edges("extract", should_continue, {...})
    # graph.add_edge("clarify", END)
    # graph.add_edge("search", "rerank")
    # graph.add_edge("rerank", "answer")
    # graph.add_edge("answer", END)

    return graph.compile(checkpointer=checkpointer or MemorySaver())
