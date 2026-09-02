# megatron

_Automated SFT pipeline for Terminal-Bench style tasks._

Megatron turns agent trajectories from terminal-based task benchmarks into
training data for **supervised fine-tuning (SFT)** — then fine-tunes a base LLM
so it learns the behaviors your agents already get right.

The pitch is simple: rather than hand-curating SFT examples, you let an agent
attempt real terminal tasks, keep the runs that succeeded, and use them as
ground-truth demonstrations. Megatron automates that whole chain — from raw
trajectories to a fine-tuned model you can actually deploy.

## Where we are: Stage 1 (runnable skeleton)

This is early days, so what's real right now is the **pipeline skeleton** —
the foundation every later stage plugs into. It's not glamorous, but it means
the architecture is stable before we start burning GPU-hours.

Today Megatron can already:

- **Validate your config** before anything runs — a bad value fails fast,
  not halfway through a run.
- **Model the core data** (tasks, trajectories, run records) as typed Pydantic
  objects in `src/auto_sft/models/`.
- **Store artifacts** on local disk or in S3, behind one clean interface.
- **Discover and load your tasks**, then split them into honest
  train / validation / held-out test sets with a reproducible seed.
- **Report clearly** — a per-stage report at the end of every run plus a
  machine-readable `pipeline/manifest.json` in the artifact store.

The four heavy stages — trajectory generation, dataset building, SFT training,
and artifact export — are declared as stubs for now. They arrive one by one in
the next milestones.

## What's next

A quick look at the road ahead:

| Stage | What it will do |
| --- | --- |
| Generation | Run agents against tasks and capture trajectories |
| Dataset | Turn successful trajectories into SFT-ready examples |
| Training | Fine-tune a base LLM (HF/TRL stack) on those examples |
| Export | Push the finished model and artifacts where you need them |

## Project layout

```
configs/pipeline.yaml        pipeline-wide configuration
examples/sample_task.yaml    a starter Terminal-Bench style task
src/auto_sft/
  cli.py                     the `auto-sft` entry point
  config.py                  typed config models + YAML loading
  logging.py                 rich logging helpers
  models/                    Task, Trajectory, RunRecord
  pipeline/runner.py         stage orchestration
  storage/                   local + S3 artifact stores
tests/                       the pytest suite
```

## Getting started

You'll need **Python 3.12+** and [uv](https://docs.astral.sh/uv/). Then:

```bash
uv sync               # install base + dev dependencies
make run-smoke        # exercise the whole skeleton end-to-end
```

`make run-smoke` runs the full pipeline against `examples/` and writes a
manifest into the artifact store — no GPUs, no API keys, no tasks required.

## Using the CLI

```bash
auto-sft run --config configs/pipeline.yaml --smoke
auto-sft run --config configs/pipeline.yaml --verbose
auto-sft version
```

Two flags worth knowing:

- `--smoke` — a fast pass that exercises the skeleton and tolerates a missing
  `tasks_dir` (it falls back to `examples/`), so a fresh checkout just works.
- `--verbose` — flips on debug logging if you want to see under the hood.

## Configuring the pipeline

Everything lives in `configs/pipeline.yaml`, with typed sections for the
pipeline, model, generation, training, cloud, and storage. A few highlights:

- **Pipeline** — name, random seed, task directory, and the train/validation/test
  split ratios. The held-out test set is *never* used to generate trajectories.
- **Storage** — switch from local disk to S3 by changing one block
  (`type: s3` plus bucket/prefix); credentials come from `S3_*` env vars.
- **Model & training** — the defaults target a LoRA fine-tune of
  `Qwen/Qwen2.5-Coder-7B-Instruct`, but everything is configurable.

Secrets and endpoint URLs live in a `.env` file (see `.env.example` for the
full list).

## Development

```bash
make test        # run the test suite
make lint        # ruff lint check
make format      # ruff format
make install-all # base + train + terminal-bench extras
```

The test suite and lint stay green as part of the workflow — not an afterthought.

## License

MIT — see [LICENSE](LICENSE).