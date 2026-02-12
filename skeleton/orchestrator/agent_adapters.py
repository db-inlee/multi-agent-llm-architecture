"""오케스트레이터-에이전트 간 브릿지 어댑터 모듈."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
import logging

from .schemas import OrchestratorState, HandoffDecision

logger = logging.getLogger(__name__)


@dataclass
class AgentCacheConfig:
    """에이전트별 캐시 설정."""
    enabled: bool = False
    ttl: int = 3600
    cache_name: str = ""


class BaseAgentAdapter(ABC):
    """에이전트 어댑터 기본 클래스. process()와 extract_slots()를 구현해야 함."""

    def __init__(self, cache_manager=None, cache_config: AgentCacheConfig = None):
        self.cache_manager = cache_manager
        self.cache_config = cache_config or AgentCacheConfig()

    @abstractmethod
    def process(self, state: OrchestratorState) -> OrchestratorState:
        """에이전트 그래프 실행 후 결과를 OrchestratorState로 반환."""
        ...

    @abstractmethod
    def extract_slots(self, user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """전체 파이프라인 없이 도메인 슬롯만 추출."""
        ...

    def format_completion_message(
        self, response: str, state_context: Dict[str, Any], language: str = "ko"
    ) -> str:
        """응답에 다국어 푸터 추가."""
        ...

    def _get_cache_key_slots(self, state: OrchestratorState) -> Dict[str, Any]:
        """캐시 키 구성 요소 생성 (에이전트별 오버라이드)."""
        return {}

    def _should_cache_result(self, result: OrchestratorState) -> bool:
        """결과 캐싱 여부 판단 (에이전트별 오버라이드)."""
        return False


# ---- 구체 어댑터 ----

class SkincareAgentAdapter(BaseAgentAdapter):
    """스킨케어 서브그래프 어댑터 (9노드, FAISS RAG, 슬롯 수집). 캐시 TTL 30분."""

    def __init__(self, checkpointer=None, cache_manager=None):
        super().__init__(
            cache_manager=cache_manager,
            cache_config=AgentCacheConfig(enabled=True, ttl=1800, cache_name="skincare"),
        )
        # # self.graph = build_skincare_graph(checkpointer=checkpointer)
        ...

    def process(self, state: OrchestratorState) -> OrchestratorState:
        """스킨케어 그래프에 발화 전달, 체크포인트 상태로 슬롯/근거/응답 관리."""
        ...

    def extract_slots(self, user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        ...


class RecoAgentAdapter(BaseAgentAdapter):
    """제품 추천 그래프 어댑터 (슬롯추출->검색->리랭크->응답). 캐시 TTL 1시간."""

    def __init__(self, llm_client=None, product_service=None,
                 cache_manager=None, checkpointer=None):
        super().__init__(
            cache_manager=cache_manager,
            cache_config=AgentCacheConfig(enabled=True, ttl=3600, cache_name="reco"),
        )
        ...

    def process(self, state: OrchestratorState) -> OrchestratorState:
        """추천 그래프에 발화 전달, 보완질문/검색/리랭크 내부 처리."""
        ...

    def extract_slots(self, user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        ...


class ASAgentAdapter(BaseAgentAdapter):
    """AS 에이전트 어댑터 (보증/기기 이슈). 건건이 다르므로 캐시 미사용."""

    def __init__(self, checkpointer=None):
        super().__init__(cache_config=AgentCacheConfig(enabled=False))
        ...

    def process(self, state: OrchestratorState) -> OrchestratorState:
        ...

    def extract_slots(self, user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        ...


class CSAgentAdapter(BaseAgentAdapter):
    """CS 에이전트 어댑터 (주문조회, 제품정보, FAQ). 캐시 TTL 15분."""

    def __init__(self, checkpointer=None, cache_manager=None):
        super().__init__(
            cache_manager=cache_manager,
            cache_config=AgentCacheConfig(enabled=True, ttl=900, cache_name="cs"),
        )
        ...

    def process(self, state: OrchestratorState) -> OrchestratorState:
        ...

    def extract_slots(self, user_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        ...
