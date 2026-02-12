"""마크다운 문서 로더."""

from __future__ import annotations
from pathlib import Path
from typing import List
from langchain_community.document_loaders import UnstructuredMarkdownLoader


def load_markdown(md_path: str) -> List:
    """마크다운 파일을 Document 리스트로 로드."""
    path = Path(md_path)
    if not path.exists():
        raise FileNotFoundError(md_path)
    loader = UnstructuredMarkdownLoader(str(path))
    return loader.load()
