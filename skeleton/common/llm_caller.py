"""통합 LLM 호출 레이어 — LLMCallBuilder.

에이전트 간 LLM 호출 코드 ~80% 중복 제거.
캐싱/재시도/로깅 통합, Pydantic 자동 검증, 호출별 성능 모니터링.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, ValidationError
import json
import hashlib
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMCallConfig(BaseModel):
    """LLM 호출 설정."""
    model: str = "gpt-4o"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    timeout_s: float = 30.0
    max_retries: int = 2
    cache_ttl: int = 3600
    use_cache: bool = True


class LLMCallStats(BaseModel):
    """호출별 통계."""
    call_id: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: int = 0
    cached: bool = False
    timestamp: str


class LLMCallBuilder:
    """통합 LLM 호출 빌더.

    파이프라인: 캐시 확인 → LLM 호출 → JSON 보정 → Pydantic 검증 → 캐시 저장 → 통계 기록.
    """

    def __init__(self, llm_client, cache_manager=None, default_config: Optional[LLMCallConfig] = None):
        """llm_client: OpenAILLM (.chat() 필수), cache_manager: CacheManager (선택)."""
        ...

    # ---- 메인 호출 ----

    def call(
        self,
        *,
        system: str,
        user: str,
        model: Optional[str] = None,
        output_schema: Optional[Type[BaseModel]] = None,
        use_tools: bool = False,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict[str, str]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        cache_key: Optional[str] = None,
        use_cache: Optional[bool] = None,
        cache_ttl: Optional[int] = None,
        parse_json: bool = False,
        json_coerce: bool = False,
        fallback_value: Optional[Any] = None,
    ) -> Union[str, Dict[str, Any], BaseModel]:
        """통합 LLM 호출. 캐싱 + Pydantic 검증 + 통계 수집."""
        ...

    # ---- 편의 메서드 ----

    def call_json(self, system: str, user: str, output_schema: Type[BaseModel], **kwargs) -> BaseModel:
        """JSON 응답 + Pydantic 검증 단축 호출."""
        ...

    def call_with_tools(
        self, system: str, user: str, tools: List[Dict[str, Any]],
        output_schema: Optional[Type[BaseModel]] = None, **kwargs,
    ) -> Union[Dict[str, Any], BaseModel]:
        """Tool calling + Pydantic 검증 단축 호출."""
        ...

    # ---- 내부 헬퍼 ----

    def _generate_call_id(self) -> str:
        """호출 ID 생성 (타임스탬프 기반)."""
        ...

    def _generate_cache_key(self, model: str, system: str, user: str) -> str:
        """캐시 키 생성: MD5(model|system|user). session_id 미포함 → 크로스 세션 히트."""
        ...

    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """캐시 조회."""
        ...

    def _set_to_cache(self, cache_key: str, value: Any, ttl: int) -> None:
        """캐시 저장."""
        ...

    def _extract_tool_response(self, resp: Dict[str, Any]) -> Dict[str, Any]:
        """tool_call arguments 추출."""
        ...

    def _coerce_json(self, text: str) -> str:
        """비정상 JSON 보정: 코드펜스 제거, 마지막 JSON 객체 추출."""
        ...

    def _process_output(
        self, raw_output: Union[str, Dict[str, Any]],
        output_schema: Optional[Type[BaseModel]], parse_json: bool,
        fallback_value: Optional[Any] = None,
    ) -> Union[str, Dict[str, Any], BaseModel]:
        """출력 처리: JSON 파싱 → Pydantic 검증. 실패 시 fallback_value 반환."""
        ...

    def _record_stats(self, call_id: str, model: str, resp: Dict[str, Any], duration_ms: int, cached: bool) -> None:
        """호출별 통계 기록 (토큰, 지연시간, 캐시 상태)."""
        ...

    # ---- 모니터링 ----

    def get_stats_summary(self) -> Dict[str, Any]:
        """집계 통계 반환 (총 호출, 캐시 히트율, 평균 지연시간, 총 토큰)."""
        ...

    def reset_stats(self) -> None:
        """통계 초기화."""
        ...
