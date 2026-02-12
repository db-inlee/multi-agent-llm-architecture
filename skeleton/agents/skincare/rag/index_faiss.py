"""FAISS 벡터 인덱스 빌더 (디스크 캐싱 지원)."""

from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import List, Optional
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from .embeddings import get_embeddings

logger = logging.getLogger(__name__)

# 디스크 캐시 경로
FAISS_CACHE_DIR = os.getenv("FAISS_CACHE_DIR", "data/faiss_cache")


def build_faiss_from_docs(
    docs: List[Document],
    embed_model: Optional[str] = None,
) -> FAISS:
    """Document 리스트를 임베딩하여 FAISS 인덱스 생성."""
    ...


def build_faiss_from_docs_cached(
    docs: List[Document],
    cache_name: str = "skincare",
    embed_model: Optional[str] = None,
) -> FAISS:
    """디스크 캐싱된 FAISS 인덱스.

    1) cache_path가 존재하면 load_local로 즉시 로드
    2) 없으면 from_documents로 빌드 후 save_local로 저장
    서버 재시작 시 임베딩 재계산 없이 로드 가능.
    """
    ...
