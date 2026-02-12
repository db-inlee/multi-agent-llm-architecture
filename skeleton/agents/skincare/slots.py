"""스킨케어 슬롯 추출 (정규식 퀵패스 + LLM 폴백)."""

from __future__ import annotations
import json
import re
from typing import Dict, Any, List, Optional

# # from .llm import get_chat
# # from .prompts import load_prompt


# ---- 퀵패스 추출기 (규칙 기반, 0ms) ----

# 피부타입 정규식 패턴
_SKIN_TYPE_PATTERNS = {
    "oily":        re.compile(r"(지성|오일리|기름|번들)"),
    "dry":         re.compile(r"(건성|건조|당김|각질)"),
    "combination": re.compile(r"(복합|혼합|T존)"),
    "sensitive":   re.compile(r"(민감|예민|자극|홍조|붉)"),
}

# 고민 키워드 -> 정규화된 고민명
_CONCERN_KEYWORDS: Dict[str, str] = {
    # # "acne": 여드름 관련 키워드,
    # # "pore": 모공 관련 키워드,
    # # "wrinkle": 주름 관련 키워드,
    # # "pigmentation": 색소침착 관련 키워드,
    # # ... (20+ 카테고리)
}


def quick_extract_skin_type(utterance: str) -> Optional[str]:
    """정규식으로 피부타입 추출. 매칭되면 첫 번째 반환, 아니면 None."""
    for skin_type, pattern in _SKIN_TYPE_PATTERNS.items():
        if pattern.search(utterance):
            return skin_type
    return None


def scan_concern_keywords(utterance: str) -> List[str]:
    """키워드 스캔으로 스킨케어 고민 목록 추출."""
    ...


# ---- LLM 기반 추출 ----

def _invoke_json(prompt, values: Dict[str, Any]) -> Dict[str, Any]:
    """gpt-4o-mini로 프롬프트 실행 후 JSON 파싱. 실패 시 안전한 기본값 반환."""
    ...


def llm_extract_slots(
    utterance: Any,
    known: Dict[str, Any] | None = None,
    conversation_history: Optional[List[Dict]] = None,
    asked_ingredient_avoid: bool = False,
    conversation_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """
    슬롯 추출 메인 진입점.

    1. 정규식으로 피부타입 추출 (0ms)
    2. 키워드 스캔으로 고민 추출 (0ms)
    3. 필수 슬롯 모두 있으면 _invoke_json 스킵, 인텐트 분류만 수행
    4. 고민은 있는데 피부타입 없으면 LLM 없이 수집 요청
    5. 나머지 경우 _invoke_json으로 풀 LLM 추출
    """
    ...


def llm_classify_intent(
    utterance: Any,
    conversation_history: Optional[List[Dict]] = None,
    asked_ingredient_avoid: bool = False,
    conversation_stage: Optional[str] = None,
) -> Dict[str, Any]:
    """슬롯 이미 채워진 경우 인텐트만 경량 분류."""
    ...


def merge_slots(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Any]:
    """기존 슬롯에 새 슬롯 병합 (비어있지 않은 기존값 우선)."""
    ...


def llm_check_dont_know_response(utterance: str) -> bool:
    """유저가 피부타입을 모른다고 답했는지 감지."""
    ...


def llm_generate_indirect_skin_question(concerns: List[str]) -> str:
    """일상 습관으로 피부타입을 유추할 수 있는 간접 질문 생성."""
    ...


def llm_infer_skin_type_from_response(response: str) -> Optional[str]:
    """유저의 피부 습관 설명에서 피부타입 추론."""
    ...
