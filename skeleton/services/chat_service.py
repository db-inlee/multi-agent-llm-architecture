"""SSE 스트리밍 채팅 서비스."""

from __future__ import annotations
import logging
import time
import uuid
from typing import Dict, Any, Optional, AsyncGenerator

logger = logging.getLogger(__name__)

# 그래프 노드 실행 중 표시할 진행 메시지
THINKING_MESSAGES: Dict[str, list] = {
    "ingest":           ["Analyzing your question..."],
    "llm_router":       ["Finding the right specialist..."],
    "agent_dispatcher":  ["Connecting to specialist..."],
    "skincare_agent":   ["Analyzing your skin concerns..."],
    "reco_agent":       ["Searching for products..."],
    "cs_agent":         ["Looking up your inquiry..."],
    "as_agent":         ["Checking service information..."],
    "response_formatter": ["Preparing your answer..."],
}


class ChatService:
    """FastAPI 엔드포인트와 오케스트레이터 그래프를 연결하는 SSE 스트리밍 서비스."""

    def __init__(self, session_store, orchestrator_graph):
        """session_store: 세션 관리, orchestrator_graph: 컴파일된 LangGraph."""
        ...

    async def process_message_stream(
        self,
        session_id: str,
        message: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        유저 메시지를 처리하고 SSE 이벤트를 yield.

        흐름: PipelineTracer 생성 -> 상태 구성 -> 그래프 실행
        -> thinking 이벤트 -> 첫 토큰(TTFT) -> token 이벤트
        -> metadata/done -> 에러 시 체크포인트 복구
        """
        ...

    async def process_message(
        self,
        session_id: str,
        message: str,
    ) -> Dict[str, Any]:
        """비스트리밍 버전. 전체 응답 dict 반환."""
        ...

    def _build_response(
        self,
        session_id: str,
        state: "OrchestratorState",
        processing_time_ms: int,
    ) -> Dict[str, Any]:
        """응답 페이로드 조립 (message_id, agent, response, intent, 타이밍 등)."""
        ...

    async def _try_recover_from_checkpoint(
        self,
        session_id: str,
        current_turn: int,
    ) -> Optional["OrchestratorState"]:
        """실패 시 체크포인터에서 마지막 정상 상태 로드."""
        ...

    def _should_attempt_recovery(self, retry_count: int, max_retries: int = 3) -> bool:
        ...

    def _create_recovery_response(
        self,
        session_id: str,
        retry_count: int,
        suggest_new_session: bool = False,
    ) -> str:
        """복구 상태를 포함한 유저 대면 에러 메시지 생성."""
        ...

    @staticmethod
    def generate_message_id() -> str:
        return uuid.uuid4().hex[:12]
