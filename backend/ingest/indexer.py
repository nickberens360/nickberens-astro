from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import List, Tuple

# Prefer the external package to silence deprecation
try:
    from langchain_chroma import Chroma  # pip install langchain-chroma
except Exception:  # fallback if not installed yet
    from langchain_community.vectorstores import Chroma

from langchain.docstore.document import Document

from .chunking import splitter_for_ext
from .loaders import load_doc
from .manifest import Manifest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _with_metadata(docs: List[Document], path: Path) -> List[Document]:
    ext = path.suffix.lower().lstrip(".")
    for d in docs:
        d.metadata = {
            **(d.metadata or {}),
            "path": str(path),
            "filename": path.name,
            "ext": ext,
            "mtime": path.stat().st_mtime,
        }
    return docs


def sync_knowledge(
    base: str = "backend/knowledge", chroma_dir: str = "backend/.chroma", embeddings=None
) -> Tuple[int, int]:
    """
    Ingest files and persist chunks to Chroma.
    Returns: (files_ingested_count, total_chunks_indexed)
    """
    base_path = Path(base)
    base_path.mkdir(parents=True, exist_ok=True)

    chroma_dir_path = Path(chroma_dir)
    chroma_dir_path.mkdir(parents=True, exist_ok=True)

    manifest = Manifest(chroma_dir_path / "manifest.json")
    vs = Chroma(collection_name="knowledge", persist_directory=str(chroma_dir), embedding_function=embeddings)

    files = [p for p in base_path.rglob("*") if p.is_file() and not p.name.startswith(".")]
    current_keys = [str(p) for p in files]

    files_ingested = 0
    chunks_total = 0

    # Upsert/Update changed files
    for path in files:
        digest = sha256_file(path)
        entry = manifest.get(str(path))
        if entry and entry.get("sha256") == digest:
            continue  # unchanged

        # delete old chunks if present
        if entry and entry.get("doc_ids"):
            try:
                vs.delete(ids=entry["doc_ids"])
            except Exception:
                pass

        raw_docs = load_doc(path)
        if not raw_docs:
            # Skip files that produce no documents (e.g., images)
            continue

        docs = _with_metadata(raw_docs, path)
        splitter = splitter_for_ext(path.suffix)
        chunks = splitter.split_documents(docs)

        if not chunks:
            # Skip if no chunks were produced
            continue

        ids = vs.add_documents(chunks)  # returns IDs
        manifest.set(
            str(path),
            {
                "sha256": digest,
                "mtime": path.stat().st_mtime,
                "doc_ids": ids,
                "indexed_at": time.time(),
            },
        )

        files_ingested += 1
        chunks_total += len(ids)

    # Remove deleted files
    for stale in manifest.keys_not_in(current_keys):
        entry = manifest.get(stale)
        if entry and entry.get("doc_ids"):
            try:
                vs.delete(ids=entry["doc_ids"])
            except Exception:
                pass
        manifest.delete(stale)

    manifest.save()
    # Newer versions of Chroma auto-persist, no need to call persist()
    return files_ingested, chunks_total
