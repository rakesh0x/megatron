"""Pipeline runner.

The runner owns the pipeline lifecycle. It:

- validates and normalises the pipeline configuration,
- prepares the artifact store and the output workspace,
- discovers and loads task definitions (``pipeline.tasks_dir``),
- computes honest train / validation / test splits,
- records a per-stage report and writes pipeline metadata into the store.

Trajectory generation runs standalone via ``auto-sft run-task`` (see
``src/auto_sft/harness.py``); dataset building, SFT training and artifact
export are declared as *stubs* until they are implemented: they keep the
pipeline shape (and the run report) stable, and are filled in milestone
by milestone.
"""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from rich.table import Table

from auto_sft.config import AppConfig
from auto_sft.logging import console, get_logger
from auto_sft.models.task import Task
from auto_sft.storage import ArtifactStore, StoreError, get_store

log = get_logger("pipeline")


class PipelineError(RuntimeError):
    """Raised when a pipeline stage fails."""


class StageReport:
    """A single stage outcome: name, status and human-readable detail."""

    def __init__(self, name: str, status: str, detail: str = "") -> None:
        self.name = name
        self.status = status  # "ok" | "stub" | "skipped" | "error"
        self.detail = detail

    def as_dict(self) -> dict[str, str]:
        return {"status": self.status, "detail": self.detail}


class PipelineRunner:
    """Runs the pipeline stages in order."""

    # Stages implemented by later milestones; declared now so the pipeline
    # shape and the run report stay stable.
    STUB_STAGES = (
        "build_dataset",
        "train",
        "export_artifacts",
    )
    STUB_HINTS = {  # noqa: RUF012 - constant, never mutated
        "build_dataset": "not implemented yet",
        "train": "not implemented yet",
        "export_artifacts": "not implemented yet",
    }

    def __init__(self, config: AppConfig, store: ArtifactStore | None = None) -> None:
        self.config = config
        self.store = store or get_store(
            type=config.storage.type,
            base_dir=config.storage.base_dir,
            bucket=config.storage.bucket,
            prefix=config.storage.prefix,
        )
        self.reports: list[StageReport] = []
        self.tasks: list[Task] = []
        self.splits: dict[str, list[str]] = {"train": [], "validation": [], "test": []}

    # -- public API ---------------------------------------------------

    def run(self, *, smoke: bool = False) -> dict[str, Any]:
        """Execute the pipeline; return a machine-readable summary."""
        log.info(
            "pipeline %r starting (smoke=%s, seed=%d)",
            self.config.pipeline.name,
            smoke,
            self.config.pipeline.seed,
        )
        self.reports.append(
            StageReport("validate_config", "ok", self._validate_config())
        )
        self.reports.append(
            StageReport("prepare_workspace", "ok", self._prepare_workspace())
        )

        tasks = self._load_tasks(smoke=smoke)
        self.tasks = tasks
        status = "ok" if tasks else "skipped"
        self.reports.append(
            StageReport("load_tasks", status, f"{len(tasks)} task(s) loaded")
        )

        n_train, n_valid, n_test = self._split_tasks(tasks)
        split_detail = f"train={n_train} validation={n_valid} test={n_test}"
        if tasks and (n_valid == 0 or n_test == 0):
            split_detail += " (warning: empty split — add more tasks)"
            log.warning(
                "split produced empty validation/test sets with %d task(s); "
                "add more tasks for honest evaluation",
                len(tasks),
            )
        self.reports.append(
            StageReport(
                "split_tasks",
                "ok" if tasks else "skipped",
                split_detail,
            )
        )

        try:
            from auto_sft.stages.generate import run_generation

            self.reports.append(
                run_generation(self.config, self.tasks, self.splits, self.store)
            )
        except Exception as exc:  # noqa: BLE001 - report failure, don't crash
            log.warning("generation stage failed: %s", exc)
            self.reports.append(StageReport("generate_trajectories", "error", str(exc)))

        for name in self.STUB_STAGES:
            self.reports.append(
                StageReport(name, "stub", self.STUB_HINTS.get(name, "not implemented yet"))
            )

        self._write_manifest(smoke=smoke)
        self._print_report()

        summary = {
            "pipeline": self.config.pipeline.name,
            "smoke": smoke,
            "seed": self.config.pipeline.seed,
            "stages": {r.name: r.as_dict() for r in self.reports},
            "splits": {k: len(v) for k, v in self.splits.items()},
        }
        log.info("pipeline %r finished", self.config.pipeline.name)
        return summary

    # -- stages -------------------------------------------------------

    def _validate_config(self) -> str:
        splits = self.config.pipeline.splits
        total = splits.train + splits.validation + splits.test
        if abs(total - 1.0) > 1e-6:
            raise PipelineError(f"split proportions must sum to 1.0, got {total}")
        return f"train={splits.train} validation={splits.validation} test={splits.test}"

    def _prepare_workspace(self) -> str:
        # The store factory already creates the base dir; verify it is usable.
        try:
            self.store.write_text("pipeline/.keep", "")
        except StoreError as exc:
            raise PipelineError(f"cannot write to artifact store: {exc}") from exc
        return f"store={type(self.store).__name__}"

    def _load_tasks(self, *, smoke: bool) -> list[Task]:
        path = Path(self.config.pipeline.tasks_dir)
        if path.exists() and path.is_dir():
            return self._read_tasks(path)
        if smoke:
            return []
        raise PipelineError(
            f"tasks_dir not found: {self.config.pipeline.tasks_dir!r} "
            "(set pipeline.tasks_dir in the config or run with --smoke)"
        )

    def _read_tasks(self, directory: Path) -> list[Task]:
        tasks: list[Task] = []
        for path in sorted(directory.glob("**/*.y*ml")):
            try:
                raw = yaml.safe_load(path.read_text())
                tasks.append(Task.model_validate(raw))
            except Exception as exc:
                raise PipelineError(f"cannot parse task file {path}: {exc}") from exc
        return tasks

    def _split_tasks(self, tasks: list[Task]) -> tuple[int, int, int]:
        self.splits = {"train": [], "validation": [], "test": []}
        if not tasks:
            return (0, 0, 0)
        order = list(tasks)
        random.Random(self.config.pipeline.seed).shuffle(order)
        splits = self.config.pipeline.splits
        n_valid = round(len(order) * splits.validation)
        n_test = round(len(order) * splits.test)
        for index, task in enumerate(order):
            if index < n_valid:
                split = "validation"
            elif index < n_valid + n_test:
                split = "test"
            else:
                split = "train"
            self.splits[split].append(task.task_id)
        return (
            len(self.splits["train"]),
            len(self.splits["validation"]),
            len(self.splits["test"]),
        )

    # -- output -------------------------------------------------------

    def _write_manifest(self, *, smoke: bool) -> None:
        payload = {
            "pipeline": self.config.pipeline.name,
            "seed": self.config.pipeline.seed,
            "smoke": smoke,
            "generated_at": datetime.now(UTC).isoformat(),
            "task_count": len(self.tasks),
            "splits": self.splits,
            "stages": {r.name: r.as_dict() for r in self.reports},
        }
        self.store.write_text(
            "pipeline/manifest.json",
            json.dumps(payload, indent=2) + "\n",
        )
        log.info("manifest written to artifact store")

    def _print_report(self) -> None:
        table = Table(title=f"Pipeline report \u2014 {self.config.pipeline.name}")
        table.add_column("stage", style="bold")
        table.add_column("status")
        table.add_column("detail")
        colors = {"ok": "green", "stub": "yellow", "skipped": "grey70", "error": "red"}
        for report in self.reports:
            color = colors.get(report.status, "white")
            table.add_row(
                report.name,
                f"[{color}]{report.status}[/]",
                report.detail,
            )
        console.print(table)
