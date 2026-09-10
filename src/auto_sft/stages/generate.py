"""Trajectory generation stage: run tasks, verify, persist trajectories.

Only train/validation tasks are executed — the held-out test split is
never touched. Each (task, attempt) runs the OpenHands harness in an
isolated workspace, is scored by the task's :class:`VerifierSpec`, and
is written to the artifact store (successes AND failures).
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from auto_sft.config import AppConfig
from auto_sft.logging import get_logger
from auto_sft.models.task import Task
from auto_sft.storage import ArtifactStore

if False:  # typing only; avoids a pipeline<->stages import cycle
    from auto_sft.pipeline.runner import StageReport

log = get_logger("stage:generate")


def agent_output_text(messages: list) -> str:
    """Join assistant messages into the text the verifier sees."""
    return "\n".join(m.content for m in messages if m.role == "assistant")


def verify(task: Task, workspace: Path, output: str) -> tuple[bool, str]:
    """Score one attempt against the task verifier. Returns (success, detail)."""
    spec = task.verifier
    if spec.type == "regex":
        if not spec.pattern:
            return False, "verifier has no pattern"
        match = re.search(spec.pattern, output)
        ok = bool(match) if spec.success_on == "match" else not match
        return ok, "regex matched" if ok else "regex did not match"
    if spec.type in ("command", "script"):
        if spec.type == "command":
            if not spec.command:
                return False, "verifier has no command"
            cmd, shell = spec.command, True
        else:
            if not spec.script:
                return False, "verifier has no script"
            cmd, shell = spec.script, True
        env = {**os.environ, "AGENT_OUTPUT": output}
        try:
            proc = subprocess.run(
                cmd,
                shell=shell,
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
                timeout=spec.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, "verifier timed out"
        zero = proc.returncode == 0
        ok = zero if spec.success_on in ("match", "zero") else not zero
        return ok, f"exit={proc.returncode}"
    return False, f"unknown verifier type: {spec.type}"


def run_generation(
    config: AppConfig,
    tasks: list[Task],
    splits: dict[str, list[str]],
    store: ArtifactStore,
) -> StageReport:
    """Execute train/val tasks and persist trajectories. Never raises."""
    from auto_sft.harness import run_task
    from auto_sft.pipeline.runner import StageReport

    gen = config.generation
    model = gen.model or config.model.base_model
    api_key = os.environ.get(gen.api_key_env)
    runnable = {t.task_id: t for t in tasks}
    target_ids = [tid for split in ("train", "validation") for tid in splits.get(split, [])]

    succeeded = failed = 0
    errors: list[str] = []
    for task_id in target_ids:
        task = runnable.get(task_id)
        if task is None:
            continue
        for attempt in range(gen.num_attempts):
            ws = Path(config.pipeline.output_dir) / "workspaces" / task_id / f"attempt-{attempt}"
            try:
                traj = run_task(
                    task,
                    model=model,
                    workspace=ws,
                    attempt=attempt,
                    max_iterations=gen.max_steps,
                    api_key=api_key,
                    base_url=gen.base_url,
                )
                output = agent_output_text(traj.messages)
                ok, detail = verify(task, ws, output)
                traj.success = ok
                traj.verified = True
                traj.reward = 1.0 if ok else 0.0
                store.write_text(
                    f"trajectories/{task_id}/attempt-{attempt}.json",
                    traj.model_dump_json(indent=2) + "\n",
                )
                succeeded, failed = succeeded + ok, failed + (not ok)
                log.info("task=%s attempt=%d success=%s (%s)", task_id, attempt, ok, detail)
            except Exception as exc:  # noqa: BLE001 - one bad attempt must not kill the stage
                failed += 1
                errors.append(f"{task_id}#{attempt}: {exc}")
                log.warning("task=%s attempt=%d errored: %s", task_id, attempt, exc)

    total = succeeded + failed
    detail = f"{succeeded}/{total} succeeded"
    if errors:
        detail += f" ({len(errors)} errored)"
    status = "ok" if total else "skipped"
    return StageReport("generate_trajectories", status, detail)