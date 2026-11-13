"""Content-addressed object store for immutable raw evidence documents.

Filesystem-backed by default (S3-compatible layout) so the platform runs locally
without external services. Swap the implementation for S3/MinIO in production.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config.settings import get_settings


class ObjectStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().objects_path
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, digest: str) -> Path:
        prefix, _, rest = digest.partition(":")
        return self.root / prefix / rest[:2] / rest[2:4] / rest

    def put(self, content: bytes, *, suffix: str = ".bin") -> tuple[str, str]:
        """Store bytes and return (uri, sha256 digest). Idempotent."""
        digest = "sha256:" + hashlib.sha256(content).hexdigest()
        path = self._path_for(digest).with_suffix(suffix)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_bytes(content)
            tmp.replace(path)
        return f"object://{digest}{suffix}", digest

    def get(self, uri: str) -> bytes:
        suffix = Path(uri.split("?")[0]).suffix
        digest = uri.removeprefix("object://")
        if digest.endswith(suffix):
            digest = digest[: -len(suffix)]
        return self._path_for(digest).with_suffix(suffix).read_bytes()

    def path(self, uri: str) -> Path:
        suffix = Path(uri.split("?")[0]).suffix
        digest = uri.removeprefix("object://")[: -len(suffix)] if suffix else uri
        return self._path_for(digest).with_suffix(suffix)

    def exists(self, uri: str) -> bool:
        try:
            return self.path(uri).exists()
        except OSError:
            return False
