from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter


def splitter_for_ext(ext: str) -> RecursiveCharacterTextSplitter:
    ext = (ext or "").lower().lstrip(".")
    if ext == "pdf":
        return RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=200)
    if ext in ("md", "markdown"):
        return RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    if ext in ("html", "htm"):
        return RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    return RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
