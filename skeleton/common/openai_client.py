"""OpenAI Chat Completions API 어댑터.

용도별 타임아웃 분리, 지수 백오프 재시도, 정규화된 응답 포맷,
tool_calls JSON 파싱, 토큰/비용 로깅, 비동기 스트리밍 지원.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
import os, json, time
import logging
from openai import OpenAI, AsyncOpenAI
from openai import APIConnectionError, RateLimitError, APIStatusError, APITimeoutError

logger = logging.getLogger(__name__)


class LLMTimeout:
    """용도별 LLM 타임아웃 상수."""
    DEFAULT = 30.0       # 일반 응답 (라우팅, 간단한 Q&A)
    COMPLEX = 60.0       # 복합 추론 (tool_calls, 긴 응답)
    STREAMING = 120.0    # 스트리밍 (점진적 전달)
    QUICK = 15.0         # 빠른 판단 (분류, 키워드 추출)


class LLMTimeoutError(Exception):
    """타임아웃 초과 시 발생."""
    pass


class LLMRateLimitError(Exception):
    """Rate limit 초과 시 발생."""
    pass


class OpenAILLM:
    """OpenAI Chat Completions 래퍼.

    레거시 호환 출력 포맷, tool_choice 처리, response_format 지원,
    지수 백오프 재시도, 토큰 사용량/비용 로깅, 비동기 스트리밍.
    """

    def __init__(self, model: str = "gpt-4o-mini", timeout_s: float = 30.0, max_retries: int = 2):
        ...

    def _normalize_tools(self, tools: Optional[List[Dict[str, Any]]]) -> Optional[List[Dict[str, Any]]]:
        """도구 정의를 SDK 포맷으로 정규화."""
        ...

    def _build_tool_choice(self, tool_choice: Optional[Union[str, Dict[str, Any]]], has_tools: bool):
        """tool_choice 파라미터 빌드. auto/required/none 또는 특정 함수 강제."""
        ...

    def chat(
        self,
        *,
        model: Optional[str] = None,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        user: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        parse_tool_arguments_json: bool = False,
        timeout_s: Optional[float] = None,
        retries: Optional[int] = None,
    ) -> Dict[str, Any]:
        """동기 Chat Completion. 재시도 + 정규화된 응답 반환."""
        ...

    async def astream(
        self,
        *,
        model: Optional[str] = None,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """비동기 스트리밍 응답 (토큰 단위 yield)."""
        ...
