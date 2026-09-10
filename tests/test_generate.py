"""Tests for the generation stage (mocked harness, no LLM calls)."""

from pathlib import Path

from auto_sft.config import AppConfig
from auto_sft.models.task import Task
from auto_sft.models.trajectory import Message, Trajectory
from auto_sft.stages.generate import run_generation, verify
from auto_sft.storage import get_store


def _task(task_id="t1", **kw):
    base = {"task_id": task_id, "description": "d"}
    return Task.model_validate({**base, **kw})


def _cfg(tmp_path: Path, attempts=2) -> AppConfig:
    return AppConfig.model_validate(
        {
            "pipeline": {
                "tasks_dir": str(tmp_path / "tasks"),
                "output_dir": str(tmp_path / "artifacts"),
            },
            "generation": {"num_attempts": attempts, "model": "test-model"},
            "storage": {"type": "local", "base_dir": str(tmp_path / "artifacts")},
        }
    )


def test_verify_regex():
    task = _task(verifier={"type": "regex", "pattern": "[a-f0-9]{32}"})
    ok, _ = verify(task, Path("/tmp"), "token abc123" + "a" * 32)
    assert ok is True
    ok, _ = verify(task, Path("/tmp"), "nothing here")
    assert ok is False


def test_verify_command(tmp_path):
    task = _task(verifier={"type": "command", "command": "exit 0"})
    ok, detail = verify(task, tmp_path, "anything")
    assert ok is True
    assert "exit=0" in detail


def test_run_generation_writes_only_train_val(tmp_path, monkeypatch):
    seen: list[str] = []

    def fake_run_task(task, **kwargs):
        seen.append(task.task_id)
        return Trajectory(
            tool_id="t",
            model_id="m",
            task_id=task.task_id,
            messages=[Message(role="assistant", content=" proves DUMMY_OK")],
        )

    monkeypatch.setattr("auto_sft.harness.run_task", fake_run_task)
    cfg = _cfg(tmp_path)
    tasks = [
        _task("train-1", verifier={"type": "regex", "pattern": "DUMMY_OK"}),
        _task("val-1", verifier={"type": "regex", "pattern": "DUMMY_OK"}),
        _task("test-1", verifier={"type": "regex", "pattern": "DUMMY_OK"}),
    ]
    splits = {"train": ["train-1"], "validation": ["val-1"], "test": ["test-1"]}
    report = run_generation(cfg, tasks, splits, get_store(type="local", base_dir=str(tmp_path / "artifacts")))
    assert report.status == "ok"
    assert "4/4 succeeded" in report.detail
    assert "test-1" not in seen  # held-out test set never executed
    assert (tmp_path / "artifacts" / "trajectories" / "train-1" / "attempt-0.json").exists()


def test_run_generation_survives_harness_errors(tmp_path, monkeypatch):
    def boom(task, **kwargs):
        raise RuntimeError("no GPU today")

    monkeypatch.setattr("auto_sft.harness.run_task", boom)
    cfg = _cfg(tmp_path, attempts=1)
    report = run_generation(
        cfg, [_task("t1")], {"train": ["t1"], "validation": [], "test": []},
        get_store(type="local", base_dir=str(tmp_path / "artifacts")),
    )
    assert report.status == "ok"
    assert "0/1 succeeded" in report.detail
