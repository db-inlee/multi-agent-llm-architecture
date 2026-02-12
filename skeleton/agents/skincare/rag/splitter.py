"""문서 청킹 설정."""

from __future__ import annotations
from langchain_text_splitters import RecursiveCharacterTextSplitter


def build_splitter(chunk_size: int = 1000, chunk_overlap: int = 200):
    """RecursiveCharacterTextSplitter 생성. 기본 1000토큰, 200 오버랩."""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
