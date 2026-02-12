"""OpenAI 임베딩 래퍼."""

from __future__ import annotations
from langchain_openai import OpenAIEmbeddings


def get_embeddings(model: str = "text-embedding-3-small") -> OpenAIEmbeddings:
    """임베딩 모델 인스턴스 반환."""
    return OpenAIEmbeddings(model=model)
