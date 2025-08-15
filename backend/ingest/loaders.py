from __future__ import annotations

from pathlib import Path
from typing import List

from langchain.docstore.document import Document

# LangChain community loaders
from langchain_community.document_loaders import (
    BSHTMLLoader,
    CSVLoader,
    Docx2txtLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader,
)

try:
    from langchain_unstructured import UnstructuredLoader
except ImportError:
    # Fallback to deprecated version if new package not available
    from langchain_community.document_loaders import UnstructuredFileLoader as UnstructuredLoader

import json


def _clean_html(text: str) -> str:
    # basic cleanup; extend if needed
    return " ".join(text.split())


def _json_to_documents(path: Path) -> List[Document]:
    """
    Load arbitrary JSON without jq. For arrays, one doc per item.
    For objects, one doc (pretty-printed) + per-top-level key docs if values are large.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs: List[Document] = []
    base_meta = {
        "source": str(path),
        "filename": path.name,
        "ext": path.suffix.lower().lstrip("."),
    }

    def make_doc(payload, extra_meta=None):
        meta = {**base_meta, **(extra_meta or {})}
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        return Document(page_content=text, metadata=meta)

    if isinstance(data, list):
        for i, item in enumerate(data):
            docs.append(make_doc(item, {"json_index": i}))
    elif isinstance(data, dict):
        # Whole object
        docs.append(make_doc(data))
        # Optionally break out big sections (simple heuristic)
        for k, v in data.items():
            if isinstance(v, (list, dict)):
                docs.append(make_doc(v, {"json_section": k}))
    else:
        # Fallback to string representation
        docs.append(make_doc(data))

    return docs


def load_doc(path: Path) -> List[Document]:
    path = Path(path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        docs = PyPDFLoader(str(path)).load()
        return docs
    if ext in (".md", ".markdown"):
        return UnstructuredMarkdownLoader(str(path)).load()
    if ext in (".html", ".htm"):
        docs = BSHTMLLoader(str(path)).load()
        for d in docs:
            d.page_content = _clean_html(d.page_content)
        return docs
    if ext in (".docx",):
        return Docx2txtLoader(str(path)).load()
    if ext in (".txt",):
        return UnstructuredLoader(str(path)).load()  # type: ignore[no-any-return]
    if ext in (".csv",):
        return CSVLoader(str(path)).load()
    if ext in (".json",):
        return _json_to_documents(path)

    # Skip non-text files and XML files (which can have complex metadata)
    if ext in (".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".xml"):
        return []

    # Fallback: treat as plain text
    try:
        return UnstructuredLoader(str(path)).load()  # type: ignore[no-any-return]
    except Exception:
        # If UnstructuredLoader fails, return empty list
        return []
