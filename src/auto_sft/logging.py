"""Logging helpers built on :mod:`logging` and :mod:`rich`."""

from __future__ import annotations

import logging
import sys

from rich.console import Console
from rich.logging import RichHandler

console = Console()

_LOGGER_NAME = "auto_sft"


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure and return the package logger."""
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)
    if not logger.handlers:
        handler = RichHandler(
            rich_tracebacks=True,
            show_path=False,
            console=console,
            markup=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger of the package logger."""
    if name:
        return logging.getLogger(f"{_LOGGER_NAME}.{name}")
    return logging.getLogger(_LOGGER_NAME)


def _stderr(msg: str) -> None:
    print(msg, file=sys.stderr)
