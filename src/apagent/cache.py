"""Tiny on-disk JSON cache for validated LLM outputs (also used as recorded responses)."""

import hashlib
import json
from pathlib import Path
from typing import Any


class JsonFileCache:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    @staticmethod
    def make_key(**parts: str) -> str:
        payload = json.dumps(parts, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key)
        if not path.exists():
            return None
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data

    def set(self, key: str, value: dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        tmp = self._path(key).with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self._path(key))
