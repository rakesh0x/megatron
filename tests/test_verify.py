"""Tests for Phase 4 trajectory verification (no LLM calls)."""

import json
from pathlib import Path

from auto_sft.models.task import Task
from auto_sft.models.trajectory import Message, Trajectory
from auto_sft.stages.verify import load_task_specs, verify_trajectories


def _write_traj(directory: Path, name: str, task_id: str, text: str) -> Path:
    traj = Trajectory(
        tool_id="t",
        model_id="m",
        task_id=task_id,
        messages=[Message(role="assistant", content=text)],
    )
    path = directory / name
    path.write_text(traj.model_dump_json())
    return path


def test_verify_filters_successes(tmp_path):
    trajs = tmp_path / "trajectories"
    trajs.mkdir()
    _write_traj(trajs, "a.json", "dummy-001", "the answer is DUMMY_OK indeed")
    _write_traj(trajs, "b.json", "dummy-001", "i failed, sorry")
    _write_traj(trajs, "c.json", "unknown-task", "DUMMY_OK")

    specs = {
        "dummy-001": Task.model_validate(
            {
                "task_id": "dummy-001",
                "description": "d",
                "verifier": {"type": "regex", "pattern": "DUMMY_OK"},
            }
        )
    }
    summary = verify_trajectories(trajs, specs)
    assert summary["succeeded"] == 1
    assert summary["failed"] == 1
    assert summary["skipped"] == 1  # unknown task, never scored

    reread = Trajectory.model_validate_json((trajs / "a.json").read_text())
    assert reread.success is True and reread.reward == 1.0 and reread.verified is True
    reread_b = Trajectory.model_validate_json((trajs / "b.json").read_text())
    assert reread_b.success is False and reread_b.reward == 0.0

    manifest = json.loads((trajs / "verified.json").read_text())
    assert manifest["succeeded"] == 1
    assert len(manifest["success_paths"]) == 1


def test_load_task_specs_indexes_both_dirs(tmp_path):
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    (tasks / "t.yaml").write_text("task_id: thin-1\ndescription: d\n")
    tb = tmp_path / "tb_tasks" / "x-1"
    (tb / "task.yaml").parent.mkdir(parents=True)
    (tb / "task.yaml").write_text("task_id: x-1\ncategory: cat\n")
    (tb / "instruction.md").write_text("do x\n")
    specs = load_task_specs(tasks, tmp_path / "tb_tasks")
    assert set(specs) == {"thin-1", "x-1"}
