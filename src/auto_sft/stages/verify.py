"""Phase 4 — verify stored trajectories and filter the successes.

Every trajectory on disk is re-scored against its task's verifier
(environment/verifier is the source of truth — never the model's own
"done" claim). Results are written back onto the trajectory files and
summarized in ``verified.json`` for the dataset stage.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from auto_sft.logging import get_logger
from auto_sft.models.task import Task
from auto_sft.models.trajectory import Trajectory
from auto_sft.stages.generate import agent_output_text, verify

log = get_logger("stage:verify")


def load_task_specs(tasks_dir: Path, tb_dir: Path | None = None) -> dict[str, Task]:
    """Index runnable task specs by task_id (thin + tb_tasks wrappers)."""
    specs: dict[str, Task] = {}
    if tasks_dir.is_dir():
        for path in sorted(tasks_dir.glob("*.yaml")):
            try:
                specs[Task.model_validate(yaml.safe_load(path.read_text())).task_id] = (
                    Task.model_validate(yaml.safe_load(path.read_text()))
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("skipping task file %s: %s", path, exc)
    if tb_dir and tb_dir.is_dir():
        for meta in sorted(tb_dir.glob("*/task.yaml")):
            try:
                raw = yaml.safe_load(meta.read_text()) or {}
                sibling = meta.parent / "instruction.md"
                specs[raw.get("task_id", meta.parent.name)] = Task.model_validate(
                    {
                        "task_id": raw.get("task_id", meta.parent.name),
                        "description": raw.get("category", meta.parent.name),
                        "instructions": sibling.read_text() if sibling.exists() else "",
                    }
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("skipping tb task %s: %s", meta, exc)
    return specs


def verify_trajectories(
    trajectories_dir: Path,
    specs: dict[str, Task],
    workspace_root: Path | None = None,
) -> dict:
    """Re-score every stored trajectory; return + write the summary."""
    succeeded: list[str] = []
    failed: list[str] = []
    skipped: list[str] = []
    for path in sorted(trajectories_dir.rglob("*.json")):
        if path.name == "verified.json":
            continue
        try:
            traj = Trajectory.model_validate_json(path.read_text())
        except Exception as exc:  # noqa: BLE001
            log.warning("skipping unreadable %s: %s", path, exc)
            skipped.append(str(path))
            continue
        task = specs.get(traj.task_id)
        if task is None:
            log.warning("no spec for task %s (%s)", traj.task_id, path)
            skipped.append(str(path))
            continue
        workspace = workspace_root or path.parent
        ok, detail = verify(task, workspace, agent_output_text(traj.messages))
        traj.success = ok
        traj.verified = True
        traj.reward = 1.0 if ok else 0.0
        path.write_text(traj.model_dump_json(indent=2) + "\n")
        (succeeded if ok else failed).append(str(path))
        log.info("%s -> %s (%s)", path, "success" if ok else "failure", detail)

    summary = {
        "total": len(succeeded) + len(failed),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "skipped": len(skipped),
        "success_paths": succeeded,
        "failed_paths": failed,
        "skipped_paths": skipped,
    }
    (trajectories_dir / "verified.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
