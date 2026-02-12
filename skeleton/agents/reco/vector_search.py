"""벡터 기반 제품 검색 서비스.

사전 계산된 임베딩(NPZ)과 제품 메타데이터(Parquet)를 로드하여
FAISS 또는 NumPy 코사인 유사도로 시맨틱 검색 수행.
"""

from __future__ import annotations
import os
import json
import logging
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ProductVectorSearch:
    """벡터 기반 제품 검색.

    초기화 시 임베딩 NPZ + 제품 Parquet 로드.
    FAISS IndexFlatIP(코사인)로 인덱스 구축, 없으면 NumPy 폴백.
    """

    def __init__(
        self,
        embeddings_path: str = "data/product_embeddings.npz",
        products_path: str = "data/products.parquet",
        use_faiss: bool = True,
    ):
        """임베딩/제품 데이터 로드 + FAISS 인덱스 구축."""
        ...

    def _normalize_embeddings(self):
        """NumPy L2 정규화 (FAISS 미사용 시)."""
        ...

    def _embed_query(self, query: str) -> np.ndarray:
        """OpenAI text-embedding-3-small로 쿼리 임베딩 생성."""
        ...

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        sub_category: Optional[str] = None,
        skin_type: Optional[str] = None,
        price_max: Optional[int] = None,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """시맨틱 검색.

        1) 쿼리 임베딩 → FAISS/NumPy 유사도 검색 (top_k * 5)
        2) 카테고리 필터 (계층적 매칭 규칙)
        3) 가격 필터
        4) 리뷰 요약 파싱 + review_insights 변환
        5) 상위 top_k 반환
        """
        ...

    def search_for_agent(
        self,
        query: str,
        category: Optional[str] = None,
        sub_category: Optional[str] = None,
        skin_type: Optional[str] = None,
        price_max: Optional[int] = None,
        top_k: int = 10,
    ) -> str:
        """에이전트 도구 호출용 검색. JSON 문자열 반환."""
        ...


# 싱글톤
_vector_search_instance: Optional[ProductVectorSearch] = None


def get_vector_search() -> ProductVectorSearch:
    """벡터 검색 서비스 싱글톤."""
    ...
