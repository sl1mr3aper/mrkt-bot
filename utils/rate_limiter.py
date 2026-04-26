"""Token-bucket style async rate limiter with adaptive backoff."""

from __future__ import annotations

import asyncio
import random
import time


class RateLimiter:
    """Limits the rate of async calls to ``rate`` per ``per`` seconds."""

    def __init__(self, rate: int = 30, per: float = 60.0, jitter: float = 0.3) -> None:
        if rate <= 0 or per <= 0:
            raise ValueError("rate and per must be positive")
        self._rate = rate
        self._per = per
        self._jitter = jitter
        self._allowance = float(rate)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()
        self._extra_delay = 0.0

    async def acquire(self) -> None:
        """Block until a slot is available; adds jitter for anti-bot."""
        async with self._lock:
            now = time.monotonic()
            self._allowance += (now - self._last) * (self._rate / self._per)
            if self._allowance > self._rate:
                self._allowance = float(self._rate)
            self._last = now

            if self._allowance < 1.0:
                wait = (1.0 - self._allowance) * (self._per / self._rate)
                wait += random.uniform(0, wait * self._jitter)
                await asyncio.sleep(wait + self._extra_delay)
                self._allowance = 0.0
            else:
                self._allowance -= 1.0
                if self._extra_delay:
                    await asyncio.sleep(self._extra_delay)
                # micro-jitter even on free allowance
                await asyncio.sleep(random.uniform(0, self._jitter))

    def increase_delay(self, seconds: float = 5.0) -> None:
        """Soft slow-down after rate-limit hit."""
        self._extra_delay = min(self._extra_delay + seconds, 60.0)

    def decrease_delay(self) -> None:
        """Recover from slow-down."""
        self._extra_delay = max(0.0, self._extra_delay - 1.0)

    def reset(self) -> None:
        """Reset internal state."""
        self._allowance = float(self._rate)
        self._last = time.monotonic()
        self._extra_delay = 0.0
