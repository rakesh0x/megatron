"""Abstract artifact store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class StoreError(RuntimeError):
    """Raised when an artifact store operation fails."""


class ArtifactStore(ABC):
    """Interface for persisting and reading pipeline artifacts."""

    @abstractmethod
    def write_bytes(self, key: str, data: bytes) -> str:
        """Write raw bytes under ``key``; return the artifact location."""

    @abstractmethod
    def write_text(self, key: str, text: str) -> str:
        """Write text under ``key``; return the artifact location."""

    @abstractmethod
    def read_bytes(self, key: str) -> bytes:
        """Read raw bytes stored under ``key``."""

    @abstractmethod
    def read_text(self, key: str) -> str:
        """Read text stored under ``key``."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether ``key`` exists in the store."""

    @abstractmethod
    def list(self, prefix: str = "") -> list[str]:
        """List keys under ``prefix``."""

    @abstractmethod
    def resolve(self, key: str) -> Path:
        """Return a local path for ``key`` (downloading if necessary)."""
