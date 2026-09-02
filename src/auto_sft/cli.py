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


@app.command()
def version() -> None:
    """Print the installed auto-sft version."""
    from auto_sft import __version__

    typer.echo(__version__)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
