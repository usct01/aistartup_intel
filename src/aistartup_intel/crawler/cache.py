"""HTTP response cache with conditional-request support (ETag / Last-Modified)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..config.settings import get_settings


@dataclass
class CacheEntry:
    url: str
    content_uri: str
    content_hash: str
    content_type: str
    etag: str | None = None
    last_modified: str | None = None


class ContentCache:
    def __init__(self, index_path: Path | None = None) -> None:
        settings = get_settings()
        self.index_path = index_path or (settings.objects_path.parent / "cache" / "index.json")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: dict[str, CacheEntry] = {}
        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            raw = json.loads(self.index_path.read_text())
            self._entries = {url: CacheEntry(**data) for url, data in raw.items()}

    def _persist(self) -> None:
        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps({u: asdict(e) for u, e in self._entries.items()}, indent=2))
        tmp.replace(self.index_path)

    def get(self, url: str) -> CacheEntry | None:
        return self._entries.get(url)

    def put(self, entry: CacheEntry) -> None:
        self._entries[entry.url] = entry
        self._persist()
