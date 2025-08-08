from __future__ import annotations

from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .indexer import sync_knowledge


class _Handler(FileSystemEventHandler):
    def __init__(self, base: str, embeddings):
        super().__init__()
        self.base = base
        self.embeddings = embeddings

    def on_any_event(self, event):
        if event.is_directory:
            return
        sync_knowledge(self.base, embeddings=self.embeddings)


def watch(base="backend/knowledge", embeddings=None):
    base_path = Path(base)
    base_path.mkdir(parents=True, exist_ok=True)
    sync_knowledge(base, embeddings=embeddings)
    handler = _Handler(base, embeddings)
    obs = Observer()
    obs.schedule(handler, str(base_path), recursive=True)
    obs.start()
    return obs
