"""Watchdog-based task supervisor."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from utils.logger import get_logger

log = get_logger(__name__)


class TaskManager:
    """Owns a set of long-running async tasks; restarts them when they crash."""

    def __init__(self, restart_delay: float = 5.0) -> None:
        self.restart_delay = restart_delay
        self._tasks: dict[str, asyncio.Task[Any]] = {}
        self._stopping = False

    def spawn(self, name: str, factory: Callable[[], Awaitable[None]]) -> None:
        if name in self._tasks:
            log.warning("task '{}' already running", name)
            return
        self._tasks[name] = asyncio.create_task(self._guard(name, factory), name=name)

    async def _guard(
        self, name: str, factory: Callable[[], Awaitable[None]]
    ) -> None:
        while not self._stopping:
            try:
                await factory()
            except asyncio.CancelledError:
                log.info("task '{}' cancelled", name)
                return
            except Exception as exc:
                log.exception("task '{}' crashed: {}", name, exc)
                if self._stopping:
                    return
                await asyncio.sleep(self.restart_delay)
            else:
                # Task returned normally — restart unless shutting down
                if self._stopping:
                    return
                log.warning("task '{}' returned unexpectedly, restarting", name)
                await asyncio.sleep(self.restart_delay)

    async def stop_all(self, timeout: float = 10.0) -> None:
        self._stopping = True
        for task in self._tasks.values():
            task.cancel()
        if not self._tasks:
            return
        await asyncio.wait(self._tasks.values(), timeout=timeout)
        self._tasks.clear()

    def names(self) -> list[str]:
        return list(self._tasks)
