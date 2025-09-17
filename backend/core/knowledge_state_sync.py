"""
Knowledge state synchronization service.

Compares filesystem, vector store, and legacy hash tracking to detect drift
and optionally reconcile by re-indexing files and cleaning up orphans.
"""

from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .knowledge_index_db import KnowledgeIndexDB

logger = logging.getLogger(__name__)


@dataclass
class ConsistencySummary:
    filesystem_files: int
    vector_docs: int
    tracked_files: int
    discovered_not_indexed: int
    changed_files: int
    vector_orphans: int
    tracked_but_missing: int


class KnowledgeStateSync:
    def __init__(self, unified_retriever: Any, *, persist_dir: str, index_dirs: List[str]) -> None:
        self.unified_retriever = unified_retriever
        self.persist_dir = persist_dir
        self.index_dirs = index_dirs
        self.db = KnowledgeIndexDB()

    # -------------------- Scanners --------------------
    def scan_filesystem(self) -> Dict[str, Dict[str, Any]]:
        files: Dict[str, Dict[str, Any]] = {}
        for directory in self.index_dirs:
            base = Path(directory)
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if p.is_file() and not p.name.startswith("."):
                    try:
                        stat = p.stat()
                        files[str(p)] = {"size": stat.st_size, "mtime": stat.st_mtime, "ext": p.suffix.lower()}
                        # Opportunistic DB upsert for discovery
                        self.db.upsert_file(str(p), size=stat.st_size, mtime=stat.st_mtime)
                    except OSError:
                        continue
        return files

    def scan_vector_store(self, max_docs: int = 100_000, page_size: int = 10_000) -> Tuple[int, Dict[str, int]]:
        """Return total vector docs and counts grouped by metadata.source."""
        searcher = getattr(self.unified_retriever, "semantic_searcher", None)
        if not searcher or not searcher.vector_store:
            return 0, {}

        collection = searcher.vector_store._collection
        try:
            total = collection.count()
        except Exception:
            total = 0

        if total == 0:
            return 0, {}

        counts: Dict[str, int] = defaultdict(int)
        fetched = 0
        offset = 0
        to_fetch = min(total, max_docs)

        while fetched < to_fetch:
            limit = min(page_size, to_fetch - fetched)
            try:
                res = collection.get(include=["metadatas"], limit=limit, offset=offset)
                metadatas = res.get("metadatas", []) if isinstance(res, dict) else []
                if not metadatas:
                    break
                for md in metadatas:
                    src = None
                    try:
                        src = md.get("source") if isinstance(md, dict) else None
                    except Exception:
                        src = None
                    if src:
                        counts[src] += 1
                n = len(metadatas)
                fetched += n
                offset += n
                if n == 0:
                    break
            except Exception as e:
                logger.warning(f"Vector scan halted at offset {offset}: {e}")
                break

        # Update DB vector_count snapshots
        for path, vc in counts.items():
            try:
                self.db.update_vector_count(path, vector_count=vc)
            except Exception:
                pass

        return total, dict(counts)

    def read_hash_tracking(self) -> Dict[str, Any]:
        try:
            meta_path = Path(self.persist_dir) / "index_metadata.json"
            if not meta_path.exists():
                return {}
            with meta_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to read index_metadata.json: {e}")
            return {}

    # -------------------- Diff & Reconcile --------------------
    def build_diff(
        self, *, fs: Dict[str, Dict[str, Any]], vcounts: Dict[str, int], tracked: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        fs_paths = set(fs.keys())
        vec_paths = set(vcounts.keys())
        tracked_paths = set(tracked.keys())

        discovered_not_indexed: List[str] = []
        changed_files: List[str] = []
        vector_orphans: List[str] = []
        tracked_but_missing: List[str] = []

        # Discovered but not indexed (FS exists, vector_count==0)
        for p in fs_paths:
            if vcounts.get(p, 0) == 0:
                discovered_not_indexed.append(p)

        # Changed files — compare mtime/hash vs DB/legacy when available
        for p in fs_paths & (vec_paths | tracked_paths):
            db_row = self.db.get_by_path(p)
            fs_mtime = fs[p].get("mtime")
            fs_size = fs[p].get("size")
            # Heuristic: if DB has older mtime/size or legacy hash mismatches, mark as changed
            legacy_entry = tracked.get(p)
            legacy_hash = legacy_entry if isinstance(legacy_entry, str) else (legacy_entry or {}).get("hash")
            if db_row:
                db_mtime = db_row.get("mtime")
                db_size = db_row.get("size")
                if (db_mtime and fs_mtime and fs_mtime > db_mtime + 1) or (db_size and fs_size and fs_size != db_size):
                    changed_files.append(p)
            else:
                # No DB row yet, but present in vector/tracked; conservatively treat as changed
                changed_files.append(p)
            # If no vector docs but tracked hash exists, also mark
            if vcounts.get(p, 0) == 0 and legacy_hash:
                if p not in changed_files:
                    changed_files.append(p)

        # Vector orphans (in vector store but file missing on disk)
        for p in vec_paths - fs_paths:
            vector_orphans.append(p)

        # Tracked but missing (in legacy metadata but file missing on disk)
        for p in tracked_paths - fs_paths:
            tracked_but_missing.append(p)

        return {
            "discovered_not_indexed": sorted(discovered_not_indexed),
            "changed_files": sorted(set(changed_files)),
            "vector_orphans": sorted(vector_orphans),
            "tracked_but_missing": sorted(tracked_but_missing),
        }

    def summarize(
        self, diff: Dict[str, List[str]], *, fs_count: int, vec_total: int, tracked_count: int
    ) -> ConsistencySummary:
        return ConsistencySummary(
            filesystem_files=fs_count,
            vector_docs=vec_total,
            tracked_files=tracked_count,
            discovered_not_indexed=len(diff.get("discovered_not_indexed", [])),
            changed_files=len(diff.get("changed_files", [])),
            vector_orphans=len(diff.get("vector_orphans", [])),
            tracked_but_missing=len(diff.get("tracked_but_missing", [])),
        )

    def validate(self) -> Tuple[ConsistencySummary, Dict[str, List[str]]]:
        fs = self.scan_filesystem()
        vec_total, vcounts = self.scan_vector_store()
        tracked = self.read_hash_tracking()
        diff = self.build_diff(fs=fs, vcounts=vcounts, tracked=tracked)
        summary = self.summarize(diff, fs_count=len(fs), vec_total=vec_total, tracked_count=len(tracked))
        return summary, diff

    def reconcile(
        self,
        *,
        dry_run: bool = True,
        allow_deletes: bool = False,
        paths: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        summary, diff = self.validate()
        actions: Dict[str, List[str]] = {
            "reindexed": [],
            "deleted_orphans": [],
            "errors": [],
        }

        # Helper to filter selected paths
        def _select(items: Iterable[str]) -> List[str]:
            selected = list(items)
            if paths:
                selected = [p for p in selected if p in paths]
            if limit is not None:
                selected = selected[: max(0, int(limit))]
            return selected

        # Reindex candidates
        to_reindex = _select(diff.get("changed_files", []) + diff.get("discovered_not_indexed", []))

        if dry_run:
            return {
                "summary": summary.__dict__,
                "diff": diff,
                "planned": {"reindex": to_reindex, "delete_orphans": _select(diff.get("vector_orphans", []))},
            }

        # Execute reindex
        for p in to_reindex:
            try:
                ok = self.unified_retriever.reindex_file(p)
                if ok:
                    # After reindex, best-effort update DB; chunk_count unknown here
                    try:
                        # Compute hash via indexer for accuracy
                        file_hash = self.unified_retriever.content_indexer.compute_file_hash(Path(p))
                    except Exception:
                        file_hash = None
                    self.db.update_indexed(p, file_hash=file_hash, chunk_count=None, vector_count=None)
                    actions["reindexed"].append(p)
                else:
                    self.db.record_error(p, error="Reindex failed")
                    actions["errors"].append(p)
            except Exception as e:
                logger.error(f"Failed to reindex {p}: {e}")
                self.db.record_error(p, error=str(e))
                actions["errors"].append(p)

        # Delete orphans if allowed
        if allow_deletes:
            searcher = getattr(self.unified_retriever, "semantic_searcher", None)
            if searcher and searcher.vector_store:
                for p in _select(diff.get("vector_orphans", [])):
                    try:
                        ok = searcher.delete_documents_by_source(p)
                        if ok:
                            self.db.update_status(p, status="missing_file")
                            actions["deleted_orphans"].append(p)
                        else:
                            actions["errors"].append(p)
                    except Exception as e:
                        logger.error(f"Failed to delete orphan {p}: {e}")
                        actions["errors"].append(p)

        # Record last reconcile time when we actually performed actions
        try:
            if not dry_run:
                from datetime import datetime

                marker = Path(self.persist_dir) / ".last_reconcile"
                marker.write_text(datetime.now().isoformat(), encoding="utf-8")
        except Exception:
            pass

        return {"summary": summary.__dict__, "diff": diff, "actions": actions}
