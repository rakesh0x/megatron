"""S3-compatible artifact store (boto3)."""

from __future__ import annotations

import os
from pathlib import Path

from auto_sft.storage.base import ArtifactStore, StoreError


class S3ArtifactStore(ArtifactStore):
    """Stores artifacts in an S3-compatible bucket.

    Requires the ``s3`` extra (``boto3``). Credentials come from the standard
    AWS env vars or ``S3_*`` env vars (see ``.env.example``).
    """

    def __init__(self, bucket: str, prefix: str = "auto-sft") -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise StoreError(
                "boto3 is required for the S3 store; install with `uv sync --extra s3`"
            ) from exc

        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._s3 = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        )

    def _key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def write_bytes(self, key: str, data: bytes) -> str:
        self._s3.put_object(Bucket=self.bucket, Key=self._key(key), Body=data)
        return f"s3://{self.bucket}/{self._key(key)}"

    def write_text(self, key: str, text: str) -> str:
        return self.write_bytes(key, text.encode("utf-8"))

    def read_bytes(self, key: str) -> bytes:
        obj = self._s3.get_object(Bucket=self.bucket, Key=self._key(key))
        return obj["Body"].read()

    def read_text(self, key: str) -> str:
        return self.read_bytes(key).decode("utf-8")

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self._s3.head_object(Bucket=self.bucket, Key=self._key(key))
            return True
        except ClientError:
            return False

    def list(self, prefix: str = "") -> list[str]:
        full = self._key(prefix)
        keys: list[str] = []
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=full):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if self.prefix:
                    key = key[len(self.prefix) + 1 :]
                keys.append(key)
        return keys

    def resolve(self, key: str) -> Path:
        raise StoreError(
            "S3 store cannot resolve to a local path; use read_bytes/read_text"
        )
