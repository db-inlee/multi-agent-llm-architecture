"""벡터스토어 리트리버 설정."""

from __future__ import annotations
from typing import Any


def as_retriever(vectorstore: Any, k: int = 6):
    """FAISS 벡터스토어를 k-NN 리트리버로 변환."""
    retriever = vectorstore.as_retriever()
    retriever.search_kwargs.update({"k": k})
    return retriever
