"""세션 저장소 추상 인터페이스.

모든 세션 스토리지 백엔드가 구현해야 할 계약 정의.
세션 메타데이터 CRUD + OrchestratorState 영속화 지원.
백엔드 교체(인메모리 → Redis → DynamoDB)는 이 인터페이스 구현만으로 완료.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class SessionStore(ABC):
    """세션 저장소 추상 클래스."""

    @abstractmethod
    def create_session(
        self, session_id: str, user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """새 세션 생성. 생성된 세션 정보 dict 반환."""
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 ID로 조회. 없으면 None."""
        pass

    @abstractmethod
    def update_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """세션 필드 업데이트. 성공 시 True."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        """세션 및 연관 상태 삭제. 삭제 시 True."""
        pass

    @abstractmethod
    def session_exists(self, session_id: str) -> bool:
        """세션 존재 여부 확인."""
        pass

    @abstractmethod
    def get_orchestrator_state(self, session_id: str) -> Optional[Any]:
        """영속화된 OrchestratorState 로드."""
        pass

    @abstractmethod
    def save_orchestrator_state(self, session_id: str, state: Any) -> bool:
        """OrchestratorState 영속화. Pydantic v1/v2 직렬화 자동 처리."""
        pass
