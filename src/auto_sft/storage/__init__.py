"""Artifact storage abstraction.

The pipeline writes every artifact (tasks, trajectories, datasets, checkpoints,
reports) through an :class:`ArtifactStore`. This keeps the pipeline independent
of where artifacts live — a local directory today, S3-compatible object storage
(and anything else) later.
"""

from auto_sft.storage.base import ArtifactStore, StoreError
from auto_sft.storage.local import LocalArtifactStore

__all__ = ["ArtifactStore", "LocalArtifactStore", "StoreError"]


def get_store(
    *,
    type: str = "local",
    base_dir: str = "artifacts",
    bucket: str | None = None,
    prefix: str = "auto-sft",
) -> ArtifactStore:
    """Factory for artifact stores."""
    if type == "local":
        return LocalArtifactStore(base_dir=base_dir)
    if type == "s3":
        from auto_sft.storage.s3 import S3ArtifactStore

        return S3ArtifactStore(bucket=bucket or "", prefix=prefix)
    raise ValueError(f"unknown storage type: {type!r} (expected 'local' or 's3')")
