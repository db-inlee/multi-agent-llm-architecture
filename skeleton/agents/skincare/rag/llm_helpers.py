"""LLM 기반 RAG 보조: 쿼리 확장, 문서 필터링/재랭킹, 웹 검색 쿼리 생성."""

from __future__ import annotations
from typing import List, Dict, Any
from functools import lru_cache
import json
import logging

logger = logging.getLogger(__name__)


# --- 1) LLM 쿼리 확장 ---

@lru_cache(maxsize=256)
def _llm_expand_query_cached(
    primary_concern: str,
    skin_type: str,
    concerns_key: str,
    avoid_key: str,
) -> Dict[str, Any]:
    """슬롯 정보로 검색 키워드 8~14개 + 검색 쿼리 1줄 생성.

    lru_cache로 동일 조합 재사용. 실패 시 기본 키워드로 폴백.
    """
    ...


def llm_expand_query(
    primary_concern: str,
    skin_type: str,
    concerns: List[str],
    avoid: List[str],
) -> Dict[str, Any]:
    """쿼리 확장 공개 인터페이스. 리스트를 정렬된 문자열로 변환 후 캐시 호출."""
    concerns_key = ",".join(sorted(set(concerns or [])))
    avoid_key = ",".join(sorted(set(avoid or [])))
    return _llm_expand_query_cached(
        primary_concern or "", skin_type or "", concerns_key, avoid_key
    )


# --- 2) 문서 필터링 + 재랭킹 ---

def llm_filter_and_rerank_docs(
    primary_concern: str,
    skin_type: str,
    concerns: List[str],
    docs: List[Any],
    top_k: int = 3,
) -> List[int]:
    """LLM으로 검색 문서 중 primary_concern 관련 문서만 필터링, 관련도 순 재정렬.

    반환값: 유지할 문서의 인덱스 리스트.
    복합 고민(건성+여드름 등) 문맥이면 양쪽에 유효한 문서도 포함.
    실패 시 상위 top_k개 인덱스를 기본 반환.
    """
    ...


# --- 3) 웹 검색 쿼리 생성 ---

def llm_web_query(
    primary_concern: str,
    skin_type: str,
    concerns: List[str],
    avoid: List[str],
) -> str:
    """primary_concern 기반 한국어 웹 검색 쿼리 1줄 생성.

    scope_consistency_guard에서 RAG 결과가 부족할 때 웹 폴백용.
    """
    ...
