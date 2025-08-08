from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class Manifest:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: Dict[str, Any] = {}
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def get(self, key: str) -> Dict[str, Any] | None:
        return self._data.get(key)

    def set(self, key: str, value: Dict[str, Any]) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def keys_not_in(self, keys):
        ks = set(keys)
        for k in list(self._data.keys()):
            if k not in ks:
                yield k

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
