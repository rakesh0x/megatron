"""Command-line interface for the auto-sft pipeline."""

from __future__ import annotations

from pathlib import Path

import typer

from auto_sft.config import load_config
from auto_sft.logging import get_logger, setup_logging
from auto_sft.pipeline.runner import PipelineRunner

app = typer.Typer(
    name="auto-sft",
    help="Automated SFT pipeline for Terminal-Bench style tasks.",
    no_args_is_help=True,
    add_completion=False,
)

log = get_logger("cli")


@app.command()
def run(
    config: Path = typer.Option(
        "configs/pipeline.yaml",
        "--config",
        "-c",
        help="Path to the pipeline YAML configuration file.",
    ),
    smoke: bool = typer.Option(
        False,
        "--smoke",
        help="Run a fast skeleton pass; tolerates a missing tasks_dir.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable debug logging.",
    ),
) -> None:
    """Run the pipeline end-to-end (or a skeleton pass with --smoke)."""
    setup_logging(verbose=verbose)
    cfg = load_config(config)
    summary = PipelineRunner(cfg).run(smoke=smoke)
    log.info("pipeline finished: %d stages", len(summary["stages"]))


@app.command(name="run-task")
def run_task_cmd(
    task: Path = typer.Option(
        ...,
        "--task",
        "-t",
        help="Path to a task YAML file (tasks/ or tb_tasks/ style).",
    ),
    model: str = typer.Option(
        ...,
        "--model",
        "-m",
        help="LLM model id (LiteLLM format, e.g. openai/gpt-4o-mini).",
    ),
    workspace: Path = typer.Option(
        "artifacts/workspaces/task-run",
        "--workspace",
        "-w",
        help="Working directory the agent operates in.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Where to write the trajectory JSON (default: artifacts/trajectories/<task-id>.json).",
    ),
    max_iterations: int = typer.Option(30, "--max-iterations", help="Cap on agent turns."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Run one task with an OpenHands agent and save the trajectory."""
    import yaml

    from auto_sft.harness import run_task
    from auto_sft.models.task import Task

    setup_logging(verbose=verbose)
    raw = yaml.safe_load(task.read_text())
    # tb_tasks/ metadata files use a different schema; wrap minimally.
    if "instructions" not in raw and task.name != "task.yaml":
        raise typer.BadParameter(f"not a runnable task spec: {task}")
    if task.name == "task.yaml":
        sibling = task.parent / "instruction.md"
        raw = {
            "task_id": raw.get("task_id", task.parent.name),
            "description": raw.get("category", task.parent.name),
            "instructions": sibling.read_text() if sibling.exists() else "",
        }
    spec = Task.model_validate(raw)
    trajectory = run_task(
        spec, model=model, workspace=workspace, max_iterations=max_iterations
    )
    dest = output or Path("artifacts/trajectories") / f"{spec.task_id}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(trajectory.model_dump_json(indent=2) + "\n")
    typer.echo(f"trajectory: {len(trajectory.messages)} messages -> {dest}")


@app.command()
def version() -> None:
    """Print the installed auto-sft version."""
    from auto_sft import __version__

    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
