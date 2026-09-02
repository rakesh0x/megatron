"""Tests for the local artifact store."""

import pytest

from auto_sft.storage import LocalArtifactStore, StoreError


def test_write_read_roundtrip(tmp_path):
    store = LocalArtifactStore(tmp_path / "artifacts")
    store.write_text("tasks/t.jsonl", "hello\n")
    assert (tmp_path / "artifacts" / "tasks" / "t.jsonl").exists()
    assert store.read_text("tasks/t.jsonl") == "hello\n"
    assert store.exists("tasks/t.jsonl")
    assert "tasks/t.jsonl" in store.list()


def test_byte_roundtrip(tmp_path):
    store = LocalArtifactStore(tmp_path)
    store.write_bytes("bin/data.bin", b"\x00\x01")
    assert store.read_bytes("bin/data.bin") == b"\x00\x01"


def test_rejects_path_escape(tmp_path):
    store = LocalArtifactStore(tmp_path)
    with pytest.raises(StoreError):
        store.write_text("../evil.txt", "x")


def test_missing_key_raises(tmp_path):
    store = LocalArtifactStore(tmp_path)
    with pytest.raises(StoreError):
        store.read_text("nope.txt")
