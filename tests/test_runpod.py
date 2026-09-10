"""Tests for the RunPod client (mocked HTTP, no key needed)."""

import httpx
import pytest

from auto_sft.cloud.runpod import GpuOffer, RunPodClient, RunPodError


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("RUNPOD_API_KEY", raising=False)
    with pytest.raises(RunPodError):
        RunPodClient()


def test_list_gpus_parses(monkeypatch):
    payload = {
        "data": {
            "gpuTypes": [
                {
                    "id": "NVIDIA A100 80GB PCIe",
                    "displayName": "A100 80GB",
                    "memoryInGb": 80,
                    "securePrice": 1.5,
                    "communityPrice": 0.9,
                },
                {"id": "x", "displayName": "Mystery"},  # sparse entry tolerated
            ]
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload, request=request)

    monkeypatch.setenv("RUNPOD_API_KEY", "fake")
    monkeypatch.setattr(
        httpx, "post", lambda *a, **k: handler(httpx.Request("POST", "https://x"))
    )
    offers = RunPodClient().list_gpus()
    assert len(offers) == 2
    assert offers[0].cheapest() == 0.9
    assert offers[1].memory_gb is None
    assert isinstance(offers[0], GpuOffer)


def test_find_matches_partial(monkeypatch):
    monkeypatch.setenv("RUNPOD_API_KEY", "fake")
    monkeypatch.setattr(
        RunPodClient, "list_gpus", lambda self: [GpuOffer("a", "H100 SXM", 80, 3.0, 2.0)]
    )
    assert RunPodClient().find("h100").display_name == "H100 SXM"
    assert RunPodClient().find("b200") is None
