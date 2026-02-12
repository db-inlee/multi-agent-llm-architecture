"""캐시 매니저 추상 인터페이스.

모든 캐시 백엔드(인메모리, Redis 등)의 계약 정의.
캐시 키는 콘텐츠 해시로 생성 (session_id 미포함 → 크로스 유저 캐시 공유).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
import hashlib
import json


class CacheManager(ABC):
    """캐시 매니저 추상 클래스."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 값 조회."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """TTL과 함께 캐시에 값 저장."""
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        """캐시에서 값 삭제."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """캐시 전체 삭제."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """키 존재 여부 확인."""
        pass

    # ---- 공용 헬퍼 ----

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """인자로 결정적 캐시 키 생성 (SHA256). 인자 순서 무관."""
        ...

    @staticmethod
    def make_router_cache_key(
        step: str, user_text: str,
        current_agent: Optional[str] = None, intent: Optional[str] = None,
        **kwargs,
    ) -> str:
        """라우터 판단 캐시 키: 'router:{step}:{hash}'. session_id 미포함."""
        ...

    @staticmethod
    def make_agent_cache_key(agent: str, query: str, **slots) -> str:
        """에이전트 응답 캐시 키: 'agent:{name}:{hash}'."""
        ...
