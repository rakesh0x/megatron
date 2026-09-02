"""Local filesystem artifact store."""

from __future__ import annotations

import shutil
from pathlib import Path

from auto_sft.storage.base import ArtifactStore, StoreError


class LocalArtifactStore(ArtifactStore):
    """Stores artifacts under a local directory.

    Keys are relative paths and are sanitized to stay inside ``base_dir``.
    """

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, key: str) -> Path:
        p = (self.base_dir / key).resolve()
        if not p.is_relative_to(self.base_dir.resolve()):
            raise StoreError(f"key escapes base dir: {key!r}")
        return p

    def write_bytes(self, key: str, data: bytes) -> str:
        p = self._safe_path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return str(p)

    def write_text(self, key: str, text: str) -> str:
        p = self._safe_path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return str(p)

    def read_bytes(self, key: str) -> bytes:
        p = self._safe_path(key)
        if not p.exists():
            raise StoreError(f"artifact not found: {key}")
        return p.read_bytes()

    def read_text(self, key: str) -> str:
        return self.read_bytes(key).decode("utf-8")

    def exists(self, key: str) -> bool:
        return self._safe_path(key).exists()

    def list(self, prefix: str = "") -> list[str]:
        root = self._safe_path(prefix)
        if not root.exists():
            return []
        return [
            str(p.relative_to(self.base_dir)) for p in root.rglob("*") if p.is_file()
        ]

    def resolve(self, key: str) -> Path:
        p = self._safe_path(key)
        if not p.exists():
            raise StoreError(f"artifact not found: {key}")
        return p

    def delete(self, key: str) -> None:
        p = self._safe_path(key)
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
