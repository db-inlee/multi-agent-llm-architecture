"""요청별 파이프라인 트레이서 (ContextVar 기반)."""

from __future__ import annotations

import time
import uuid
import logging
from contextvars import ContextVar, Token
from contextlib import contextmanager, asynccontextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class SpanRecord:
    """단일 스팬(파이프라인 구간) 기록."""
    name: str                           # 예: "router.classify_intent"
    start_offset_ms: float              # 요청 시작 시점 대비 오프셋
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraceSummary:
    """요청 하나의 전체 트레이스 요약."""
    trace_id: str
    session_id: str
    ttft_ms: Optional[float] = None
    e2e_ms: float = 0.0
    spans: List[SpanRecord] = field(default_factory=list)
    path: str = ""                      # "ingest -> llm_router -> ..."

    def to_dict(self) -> Dict[str, Any]:
        """트레이스 요약을 직렬화 가능한 dict로 변환."""
        ...


class PipelineTracer:
    """요청별 파이프라인 트레이서."""

    def __init__(self, session_id: str, trace_id: Optional[str] = None):
        self.trace_id = trace_id or uuid.uuid4().hex[:8]
        self.session_id = session_id
        self._request_start = time.monotonic()
        self._spans: List[SpanRecord] = []
        self._active_spans: Dict[str, float] = {}   # name -> 시작 monotonic
        self._ttft_ms: Optional[float] = None
        self._ttft_marked = False
        self._node_path: List[str] = []

    # --- 스팬 API ---

    def span_start(self, name: str) -> None:
        """스팬 시작 기록."""
        ...

    def span_end(self, name: str, **metadata) -> None:
        """스팬 종료 및 SpanRecord 생성."""
        ...

    @contextmanager
    def span(self, name: str, **metadata):
        """동기 컨텍스트 매니저 스팬."""
        ...

    @asynccontextmanager
    async def aspan(self, name: str, **metadata):
        """비동기 컨텍스트 매니저 스팬."""
        ...

    # --- TTFT / 노드 경로 ---

    def mark_ttft(self) -> None:
        """첫 콘텐츠 토큰 생성 시점 기록 (1회만)."""
        ...

    def mark_node(self, node_name: str) -> None:
        """노드 경로에 추가 (연속 중복 제거)."""
        ...

    # --- 종료 ---

    def finish(self) -> TraceSummary:
        """트레이스 완료 후 요약 반환."""
        ...


# --- ContextVar 전역 접근 ---

_current_tracer: ContextVar[Optional[PipelineTracer]] = ContextVar(
    "_current_tracer", default=None
)


def get_tracer() -> Optional[PipelineTracer]:
    """현재 요청의 PipelineTracer 반환 (미설정 시 None)."""
    return _current_tracer.get()


def set_tracer(tracer: PipelineTracer) -> Token:
    """현재 async 컨텍스트에 PipelineTracer 바인딩."""
    return _current_tracer.set(tracer)


def reset_tracer(token: Token) -> None:
    """ContextVar를 이전 값으로 복원."""
    _current_tracer.reset(token)
