# megatron

Automated SFT pipeline for Terminal-Bench style tasks.

Builds SFT training data from agent trajectories on terminal-based task
benchmarks, then fine-tunes a base LLM on the successful behaviors.

## Status — Stage 1 (runnable skeleton)

Stage 1 delivers a runnable end-to-end skeleton:

- Typed configuration (`src/auto_sft/config.py`) loaded from `configs/pipeline.yaml`
- Data models: `Task`, `Trajectory`, `RunRecord` (`src/auto_sft/models/`)
- Artifact stores: local filesystem and S3 (`src/auto_sft/storage/`)
- CLI (`auto-sft`, `src/auto_sft/cli.py`) with the `run` command
- Pipeline runner skeleton (`src/auto_sft/pipeline/runner.py`):
  validate config → prepare workspace → load tasks → train/validation/test
  splits → declare stub stages (generation, dataset, training, export)

Trajectory generation, dataset building, SFT training and artifact export
are stubbed in the runner and land in later stages.

## Quickstart

```bash
uv sync          # install base + dev dependencies
make test        # pytest
make lint        # ruff check
make run-smoke   # smoke pass over examples/sample_task.yaml
```

## CLI

```bash
auto-sft run --config configs/pipeline.yaml --smoke
auto-sft run --config configs/pipeline.yaml --verbose
```

`--smoke` runs the skeleton fast and tolerates a missing `tasks_dir` (it
falls back to `examples/`), so a fresh checkout can be exercised without any
tasks on disk.

## Layout

```
configs/pipeline.yaml   pipeline-wide configuration
examples/sample_task.yaml  example Terminal-Bench style task
src/auto_sft/
  cli.py                typer entry point
  config.py             typed config models + YAML loading
  logging.py            rich logging helpers
  models/               Task, Trajectory, RunRecord
  pipeline/runner.py    stage orchestration
  storage/              local + S3 artifact stores (ArtifactStore ABC)
tests/                  pytest suite
```

## License

MIT — see [LICENSE](LICENSE).