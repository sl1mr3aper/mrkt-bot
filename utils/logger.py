"""Loguru-based structured logger."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger as _logger

_initialised = False


def setup_logger(
    level: str = "INFO",
    log_file: str = "logs/bot.log",
    rotation: str = "1 day",
    retention: str = "30 days",
) -> Any:
    """Configure loguru. Idempotent."""
    global _initialised
    if _initialised:
        return _logger

    Path(log_file).expanduser().parent.mkdir(parents=True, exist_ok=True)

    _logger.remove()
    _logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:<7}</level> | "
            "<cyan>{name}:{function}:{line}</cyan> | "
            "<level>{message}</level>"
        ),
        backtrace=True,
        diagnose=False,
        enqueue=False,
    )
    _logger.add(
        log_file,
        level=level,
        rotation=rotation,
        retention=retention,
        encoding="utf-8",
        enqueue=True,
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<7} | "
            "{name}:{function}:{line} | {message}"
        ),
    )

    _initialised = True
    return _logger


def get_logger(name: str | None = None) -> Any:
    """Return a bound logger (optionally tagged with module name)."""
    if name:
        return _logger.bind(module=name)
    return _logger
