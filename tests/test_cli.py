"""Tests for the CLI entry point."""

import shutil
from pathlib import Path

from typer.testing import CliRunner

from auto_sft.cli import app

ROOT = Path(__file__).resolve().parents[1]

runner = CliRunner()


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    # Recent typer versions exit with 2 when no_args_is_help triggers.
    assert result.exit_code in (0, 2)
    assert "Run the pipeline" in result.output


def test_run_smoke_end_to_end(tmp_path, monkeypatch):
    from auto_sft.models.trajectory import Trajectory

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "auto_sft.harness.run_task",
        lambda task, **kwargs: Trajectory(
            tool_id="test", model_id="m", task_id=task.task_id
        ),
    )
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    for src in (ROOT / "tasks").glob("*.yaml"):
        shutil.copy(src, tasks / src.name)

    config = tmp_path / "pipeline.yaml"
    config.write_text(
        "pipeline:\n"
        f'  tasks_dir: "{tasks}"\n'
        f'  output_dir: "{tmp_path / "artifacts"}"\n'
        "storage:\n"
        "  type: local\n"
        f'  base_dir: "{tmp_path / "artifacts"}"\n'
    )

    result = runner.invoke(app, ["run", "--config", str(config), "--smoke"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "artifacts" / "pipeline" / "manifest.json").exists()
