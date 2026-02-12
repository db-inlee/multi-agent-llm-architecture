"""응답 시간 및 비용 메트릭 수집 시스템."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
import time
import logging

logger = logging.getLogger(__name__)


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """모델 가격 기준 LLM 호출 비용(USD) 추정."""
    ...


@dataclass
class NodeMetric:
    """노드별 실행 메트릭."""
    node_name: str
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    llm_calls: int = 0
    tokens_used: int = 0
    cost: float = 0.0
    state_changes: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """노드 메트릭을 직렬화 가능한 dict로 변환."""
        ...


@dataclass
class SessionMetrics:
    """세션별 집계 메트릭."""
    session_id: str
    user_id: Optional[str] = None
    started_at: str = ""
    ended_at: str = ""
    total_duration_ms: float = 0.0
    total_llm_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    nodes: List[NodeMetric] = field(default_factory=list)
    _active_nodes: Dict[str, NodeMetric] = field(default_factory=dict)
    ttft_ms: Optional[float] = None
    trace_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """세션 메트릭을 직렬화 가능한 dict로 변환."""
        ...


class MetricsStore:
    """스레드 안전 싱글턴 세션 메트릭 저장소."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._sessions: Dict[str, SessionMetrics] = {}
                    cls._instance._max_sessions = 1000
        return cls._instance

    def start_session(self, session_id: str, user_id: Optional[str] = None) -> None:
        ...

    def end_session(self, session_id: str) -> Optional[SessionMetrics]:
        ...

    def _cleanup_old_sessions(self) -> None:
        """최대 세션 수 초과 시 오래된 세션부터 제거."""
        ...

    def start_node(self, session_id: str, node_name: str) -> None:
        ...

    def end_node(
        self,
        session_id: str,
        node_name: str,
        llm_calls: int = 0,
        tokens: int = 0,
        cost: float = 0.0,
        state_changes: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> Optional[NodeMetric]:
        ...

    def record_trace(self, session_id: str, trace_summary) -> None:
        """세션 메트릭에 TraceSummary 첨부."""
        ...

    def get_recent_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        ...

    def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        ...

    def get_summary(self) -> Dict[str, Any]:
        """전체 세션 집계 통계 (TTFT p50/p95 포함)."""
        ...

    @staticmethod
    def _percentile(sorted_values: List[float], p: float) -> float:
        ...

    def reset(self) -> None:
        ...


def get_metrics_store() -> MetricsStore:
    """MetricsStore 싱글턴 반환."""
    return MetricsStore()
