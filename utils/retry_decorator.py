"""Retry helpers with exponential backoff."""

from __future__ import annotations

import asyncio
import functools
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from .exceptions import NetworkError, RateLimitError
from .logger import get_logger

T = TypeVar("T")
log = get_logger(__name__)


def retry_async(
    *,
    attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: float = 0.4,
    retry_on: tuple[type[BaseException], ...] = (NetworkError, RateLimitError, asyncio.TimeoutError),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Async retry with exponential backoff + jitter.

    Example::

        @retry_async(attempts=5)
        async def fetch():
            ...
    """

    def decorator(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args: object, **kwargs: object) -> T:
            last: BaseException | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except retry_on as exc:
                    last = exc
                    if attempt == attempts:
                        log.error(
                            "{} exhausted {} attempts: {}", fn.__name__, attempts, exc
                        )
                        raise
                    delay = min(max_delay, base_delay * 2 ** (attempt - 1))
                    delay += random.uniform(0, delay * jitter)
                    log.warning(
                        "{} attempt {}/{} failed ({}), retry in {:.2f}s",
                        fn.__name__, attempt, attempts, exc, delay,
                    )
                    await asyncio.sleep(delay)
            # Unreachable but mypy needs it
            assert last is not None
            raise last

        return wrapper

    return decorator
