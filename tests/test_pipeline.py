"""Tests for the pipeline runner skeleton."""

import json
from pathlib import Path

import pytest

from auto_sft.config import AppConfig
from auto_sft.pipeline.runner import PipelineError, PipelineRunner

ROOT = Path(__file__).resolve().parents[1]


def _config(tmp_path: Path) -> AppConfig:
    return AppConfig.model_validate(
        {
            "pipeline": {
                "name": "smoke-test",
                "tasks_dir": str(ROOT / "tasks"),
                "seed": 7,
            },
            "storage": {"type": "local", "base_dir": str(tmp_path / "artifacts")},
        }
    )


def test_smoke_run_writes_manifest(tmp_path, monkeypatch):
    from auto_sft.models.trajectory import Message, Trajectory

    def fake_run_task(task, **kwargs):
        return Trajectory(
            tool_id="test",
            model_id="test-model",
            task_id=task.task_id,
            attempt=kwargs.get("attempt", 0),
            messages=[Message(role="assistant", content=" proves DUMMY_OK")],
        )

    monkeypatch.setattr("auto_sft.harness.run_task", fake_run_task)
    runner = PipelineRunner(_config(tmp_path))
    summary = runner.run(smoke=True)
    assert summary["pipeline"] == "smoke-test"
    assert summary["stages"]["generate_trajectories"]["status"] == "ok"
    assert summary["stages"]["train"]["status"] == "stub"

    manifest = json.loads(
        (tmp_path / "artifacts" / "pipeline" / "manifest.json").read_text()
    )
    assert manifest["task_count"] == 2
    assert sorted(manifest["splits"]["train"]) == ["dummy-001", "forensics-001"]


def test_smoke_run_tolerates_missing_tasks_dir(tmp_path, monkeypatch):
    # The smoke run tolerates a missing tasks_dir (CWD-relative);
    # isolate CWD so nothing on disk can satisfy the configured dir.
    monkeypatch.chdir(tmp_path)
    cfg = AppConfig.model_validate(
        {
            "pipeline": {"tasks_dir": str(tmp_path / "missing")},
            "storage": {"type": "local", "base_dir": str(tmp_path / "artifacts")},
        }
    )
    summary = PipelineRunner(cfg).run(smoke=True)
    assert summary["stages"]["load_tasks"]["status"] == "skipped"


def test_non_smoke_requires_tasks_dir(tmp_path):
    cfg = AppConfig.model_validate(
        {
            "pipeline": {"tasks_dir": str(tmp_path / "missing")},
            "storage": {"type": "local", "base_dir": str(tmp_path / "artifacts")},
        }
    )
    with pytest.raises(PipelineError):
        PipelineRunner(cfg).run(smoke=False)


def test_split_counts_are_deterministic(tmp_path):
    tasks_dir = tmp_path / "tasks"
    tasks_dir.mkdir()
    for index in range(10):
        (tasks_dir / f"task-{index:02d}.yaml").write_text(
            f"task_id: task-{index:02d}\ndescription: task {index}\n"
        )

    def run_split_counts() -> dict[str, int]:
        cfg = AppConfig.model_validate(
            {
                "pipeline": {"tasks_dir": str(tasks_dir), "seed": 3},
                "storage": {"type": "local", "base_dir": str(tmp_path / "artifacts")},
            }
        )
        return PipelineRunner(cfg).run(smoke=True)["splits"]

    first = run_split_counts()
    assert sum(first.values()) == 10
    assert first == run_split_counts()
