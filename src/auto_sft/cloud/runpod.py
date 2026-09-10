"""RunPod client: query live GPU types, pricing, and availability.

Uses the RunPod GraphQL API (https://api.runpod.ai/graphql) over the
existing ``httpx`` dependency — no extra packages. Auth via
``RUNPOD_API_KEY`` env (see ``.env.example``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

API_URL = "https://api.runpod.ai/graphql"

GPU_TYPES_QUERY = """
query {
  gpuTypes {
    id
    displayName
    memoryInGb
    securePrice
    communityPrice
    secureSpotPrice
    communitySpotPrice
    maxGpuCount
    maxPodCount
  }
}
"""


class RunPodError(RuntimeError):
    """Raised when the RunPod API cannot be queried."""


@dataclass
class GpuOffer:
    id: str
    display_name: str
    memory_gb: float | None
    secure_price: float | None
    community_price: float | None
    secure_spot: float | None = None
    community_spot: float | None = None
    max_gpus: int | None = None

    def cheapest(self) -> float | None:
        prices = [p for p in (self.community_price, self.secure_price) if p is not None]
        return min(prices) if prices else None


class RunPodClient:
    """Thin wrapper around the RunPod GraphQL API."""

    def __init__(self, api_key: str | None = None, timeout: float = 30.0) -> None:
        key = api_key or os.environ.get("RUNPOD_API_KEY")
        if not key:
            raise RunPodError(
                "RUNPOD_API_KEY is not set (copy .env.example to .env and fill it in)"
            )
        self._key = key
        self._timeout = timeout

    def _query(self, query: str) -> dict:
        try:
            resp = httpx.post(
                API_URL,
                json={"query": query},
                headers={"Authorization": f"Bearer {self._key}"},
                timeout=self._timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
        except httpx.HTTPError as exc:
            raise RunPodError(f"RunPod request failed: {exc}") from exc
        if payload.get("errors"):
            raise RunPodError(f"RunPod API error: {payload['errors']}")
        return payload.get("data", {})

    def list_gpus(self) -> list[GpuOffer]:
        """Return all GPU types with pricing (tolerant of schema drift)."""
        data = self._query(GPU_TYPES_QUERY)
        offers = []
        for entry in data.get("gpuTypes") or []:
            offers.append(
                GpuOffer(
                    id=str(entry.get("id", "?")),
                    display_name=str(entry.get("displayName", "?")),
                    memory_gb=entry.get("memoryInGb"),
                    secure_price=entry.get("securePrice"),
                    community_price=entry.get("communityPrice"),
                    secure_spot=entry.get("secureSpotPrice"),
                    community_spot=entry.get("communitySpotPrice"),
                    max_gpus=entry.get("maxGpuCount"),
                )
            )
        return offers

    def find(self, name: str) -> GpuOffer | None:
        """Find a GPU type by (partial, case-insensitive) display name."""
        needle = name.lower()
        for offer in self.list_gpus():
            if needle in offer.display_name.lower() or needle in offer.id.lower():
                return offer
        return None
