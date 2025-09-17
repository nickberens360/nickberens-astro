"""
Knowledge Index metadata database (SQLite).

Tracks file discovery and indexing status to enable robust reconciliation
between the filesystem, vector database, and legacy hash tracking.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .database_utils import get_database_path

logger = logging.getLogger(__name__)


class KnowledgeIndexDB:
    """Lightweight SQLite wrapper for knowledge index metadata."""

    def __init__(self) -> None:
        self.db_path: Path = get_database_path("knowledge_index.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL;")
            cur.execute("PRAGMA synchronous=NORMAL;")
        except Exception:
            pass
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    dir TEXT,
                    filename TEXT,
                    ext TEXT,
                    size INTEGER,
                    mtime REAL,
                    hash TEXT,
                    status TEXT CHECK(status IN (
                        'discovered','pending_index','indexed','error','orphaned','missing_file'
                    )) NOT NULL DEFAULT 'discovered',
                    chunk_count INTEGER DEFAULT 0,
                    vector_count INTEGER DEFAULT 0,
                    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    indexed_at TIMESTAMP,
                    last_error TEXT,
                    last_error_at TIMESTAMP
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_kf_status ON knowledge_files(status)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_kf_dir ON knowledge_files(dir)")

    @staticmethod
    def _split_path(path: str) -> Dict[str, Any]:
        p = Path(path)
        return {
            "dir": str(p.parent),
            "filename": p.name,
            "ext": p.suffix.lower().lstrip("."),
        }

    def upsert_file(
        self, path: str, *, size: Optional[int] = None, mtime: Optional[float] = None, file_hash: Optional[str] = None
    ) -> None:
        parts = self._split_path(path)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO knowledge_files(path, dir, filename, ext, size, mtime, hash, status)
                VALUES (:path, :dir, :filename, :ext, :size, :mtime, :hash, COALESCE(
                    (SELECT status FROM knowledge_files WHERE path = :path), 'discovered'
                ))
                ON CONFLICT(path) DO UPDATE SET
                    dir=excluded.dir,
                    filename=excluded.filename,
                    ext=excluded.ext,
                    size=COALESCE(excluded.size, knowledge_files.size),
                    mtime=COALESCE(excluded.mtime, knowledge_files.mtime),
                    hash=COALESCE(excluded.hash, knowledge_files.hash)
                """,
                {
                    "path": path,
                    "dir": parts["dir"],
                    "filename": parts["filename"],
                    "ext": parts["ext"],
                    "size": size,
                    "mtime": mtime,
                    "hash": file_hash,
                },
            )

    def update_indexed(
        self, path: str, *, file_hash: Optional[str], chunk_count: Optional[int], vector_count: Optional[int]
    ) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE knowledge_files
                SET status='indexed', hash=COALESCE(:hash, hash),
                    chunk_count=COALESCE(:chunk_count, chunk_count),
                    vector_count=COALESCE(:vector_count, vector_count),
                    indexed_at=:indexed_at,
                    last_error=NULL, last_error_at=NULL
                WHERE path=:path
                """,
                {
                    "path": path,
                    "hash": file_hash,
                    "chunk_count": chunk_count,
                    "vector_count": vector_count,
                    "indexed_at": datetime.utcnow().isoformat(timespec="seconds"),
                },
            )

    def update_vector_count(self, path: str, *, vector_count: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE knowledge_files SET vector_count=? WHERE path=?",
                (vector_count, path),
            )

    def update_status(self, path: str, *, status: str) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE knowledge_files SET status=? WHERE path=?", (status, path))

    def record_error(self, path: str, *, error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE knowledge_files
                SET status='error', last_error=?, last_error_at=?
                WHERE path=?
                """,
                (error[:1000], datetime.utcnow().isoformat(timespec="seconds"), path),
            )

    def get_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute("SELECT * FROM knowledge_files WHERE path=?", (path,))
            row = cur.fetchone()
            if not row:
                return None
            return dict(row)

    def list_files(self, *, status: Optional[str] = None, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if status:
                cur = conn.execute(
                    "SELECT * FROM knowledge_files WHERE status=? ORDER BY filename LIMIT ? OFFSET ?",
                    (status, limit, offset),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM knowledge_files ORDER BY filename LIMIT ? OFFSET ?",
                    (limit, offset),
                )
            return [dict(r) for r in cur.fetchall()]
