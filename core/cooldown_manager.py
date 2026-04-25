"""Tracks the 60-second cooldown that MRKT enforces between buy and sell."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta


class CooldownManager:
    """Maintains per-gift_id cooldowns; supports both async waits and queries."""

    def __init__(self, default_seconds: int = 60) -> None:
        self.default = default_seconds
        self._until: dict[str, datetime] = {}
        self._events: dict[str, asyncio.Event] = {}

    def start(self, gift_id: str, seconds: int | None = None) -> datetime:
        s = seconds if seconds is not None else self.default
        until = datetime.now(UTC) + timedelta(seconds=s)
        self._until[gift_id] = until
        self._events[gift_id] = asyncio.Event()
        return until

    def remaining(self, gift_id: str) -> float:
        until = self._until.get(gift_id)
        if not until:
            return 0.0
        delta = (until - datetime.now(UTC)).total_seconds()
        return max(0.0, delta)

    def is_ready(self, gift_id: str) -> bool:
        return self.remaining(gift_id) <= 0.0

    async def wait(self, gift_id: str) -> None:
        rem = self.remaining(gift_id)
        if rem <= 0:
            return
        await asyncio.sleep(rem + 0.5)
        ev = self._events.get(gift_id)
        if ev:
            ev.set()

    def clear(self, gift_id: str) -> None:
        self._until.pop(gift_id, None)
        ev = self._events.pop(gift_id, None)
        if ev and not ev.is_set():
            ev.set()
