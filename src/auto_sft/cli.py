"""Command-line interface for the auto-sft pipeline."""

from __future__ import annotations

from pathlib import Path

import typer
from dotenv import load_dotenv

from auto_sft.config import load_config
from auto_sft.logging import get_logger, setup_logging
from auto_sft.pipeline.runner import PipelineRunner

load_dotenv()

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
        help="Run a quick pass; tolerates a missing tasks_dir.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable debug logging.",
    ),
) -> None:
    """Run the pipeline end-to-end (or a quick pass with --smoke)."""
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
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        help="LLM endpoint base URL (e.g. http://localhost:11434 for Ollama). "
        "Defaults to OPENHANDS_BASE_URL env, or localhost:11434 for ollama/ models.",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        help="LLM API key. Defaults to OPENHANDS_LLM_API_KEY / LLM_API_KEY / "
        "OPENROUTER_API_KEY / OPENAI_API_KEY env. Not needed for local Ollama.",
    ),
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
        spec,
        model=model,
        workspace=workspace,
        max_iterations=max_iterations,
        api_key=api_key,
        base_url=base_url,
    )
    dest = output or Path("artifacts/trajectories") / f"{spec.task_id}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(trajectory.model_dump_json(indent=2) + "\n")
    typer.echo(f"trajectory: {len(trajectory.messages)} messages -> {dest}")


@app.command()
def infra(
    config: Path = typer.Option(
        "configs/pipeline.yaml", "--config", "-c", help="Path to the pipeline YAML."
    ),
    live: bool = typer.Option(
        False,
        "--live",
        help="Query RunPod for live GPU pricing/availability (needs RUNPOD_API_KEY).",
    ),
    gpu: str | None = typer.Option(
        None, "--gpu", help="With --live: filter to one GPU (e.g. 'A100', 'H100')."
    ),
) -> None:
    """Show the resolved training infrastructure for this config."""
    import importlib.util

    cfg = load_config(config)
    rows = [
        ("provider", cfg.cloud.provider),
        ("gpu", f"{cfg.cloud.num_gpus}x {cfg.cloud.gpu}"),
        ("timeout_hours", str(cfg.cloud.timeout_hours)),
        ("method", cfg.training.method),
        ("safety_scan", str(cfg.training.safety_scan)),
        ("output_dir", cfg.training.output_dir),
        ("torch", "installed" if importlib.util.find_spec("torch") else "missing (uv sync --extra train)"),
        ("unsloth", "installed" if importlib.util.find_spec("unsloth") else "not installed"),
    ]
    width = max(len(k) for k, _ in rows)
    for key, value in rows:
        typer.echo(f"{key:<{width}}  {value}")

    if not live:
        return
    from auto_sft.cloud import RunPodClient, RunPodError

    try:
        client = RunPodClient()
        offers = client.list_gpus()
    except RunPodError as exc:
        typer.echo(f"live lookup failed: {exc}")
        raise typer.Exit(code=1)
    if gpu:
        offers = [
            o
            for o in offers
            if gpu.lower() in o.display_name.lower() or gpu.lower() in o.id.lower()
        ]
        if not offers:
            typer.echo(f"no RunPod GPU matching {gpu!r}")
            raise typer.Exit(code=1)
    typer.echo(f"\nRunPod live: {len(offers)} GPU type(s)")
    for offer in sorted(offers, key=lambda o: (o.cheapest() is None, o.cheapest())):
        cheapest = offer.cheapest()
        price = f"${cheapest:.3f}/hr" if cheapest is not None else "n/a"
        typer.echo(f"  {offer.display_name:<28} {offer.memory_gb}GB  from {price}")


@app.command(name="verify-trajectories")
def verify_trajectories_cmd(
    trajectories: Path = typer.Option(
        "artifacts/trajectories",
        "--trajectories",
        help="Directory holding stored trajectory JSON files.",
    ),
    tasks_dir: Path = typer.Option(
        "tasks", "--tasks-dir", help="Thin task specs directory."
    ),
    tb_dir: Path = typer.Option(
        "tb_tasks", "--tb-dir", help="Terminal-Bench style tasks directory."
    ),
) -> None:
    """Phase 4: re-verify stored trajectories, filter successes to verified.json."""
    from auto_sft.stages.verify import load_task_specs, verify_trajectories

    specs = load_task_specs(tasks_dir, tb_dir)
    summary = verify_trajectories(trajectories, specs)
    typer.echo(
        f"verified {summary['total']}: {summary['succeeded']} success, "
        f"{summary['failed']} failure, {summary['skipped']} skipped "
        f"-> {trajectories / 'verified.json'}"
    )


@app.command()
def version() -> None:
    """Print the installed auto-sft version."""
    from auto_sft import __version__

    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
