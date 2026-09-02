.PHONY: install install-train install-terminal install-all test lint format run-smoke clean

PYTHON ?= uv run python

install:
	uv sync

install-train:
	uv sync --extra train

install-terminal:
	uv sync --extra terminal-bench

install-all:
	uv sync --all-extras

test:
	$(PYTHON) -m pytest

lint:
	uv run ruff check src tests scripts

format:
	uv run ruff format src tests scripts

run-smoke:
	$(PYTHON) -m auto_sft.cli run --config configs/pipeline.yaml --smoke

clean:
	rm -rf .venv artifacts runs outputs .pytest_cache