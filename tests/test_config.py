"""Tests for typed configuration loading."""

from pathlib import Path

import pytest

from auto_sft.config import AppConfig, load_config

ROOT = Path(__file__).resolve().parents[1]


def test_load_pipeline_config():
    cfg = load_config(ROOT / "configs" / "pipeline.yaml")
    assert cfg.pipeline.name == "terminal-bench-sft-v1"
    assert (
        cfg.pipeline.splits.train
        + cfg.pipeline.splits.validation
        + cfg.pipeline.splits.test
        == pytest.approx(1.0)
    )
    assert cfg.generation.num_attempts == 4
    assert cfg.storage.type == "local"


def test_missing_config_file():
    with pytest.raises(FileNotFoundError):
        load_config(ROOT / "configs" / "nope.yaml")


def test_model_shorthand():
    cfg = AppConfig.model_validate({"model": "Qwen/Qwen2.5-Coder-7B-Instruct"})
    assert cfg.model.base_model == "Qwen/Qwen2.5-Coder-7B-Instruct"


def test_splits_must_sum_to_one():
    with pytest.raises(ValueError):
        AppConfig.model_validate(
            {"pipeline": {"splits": {"train": 0.8, "validation": 0.1, "test": 0.05}}}
        )


def test_s3_requires_bucket():
    with pytest.raises(ValueError):
        AppConfig.model_validate({"storage": {"type": "s3"}})
