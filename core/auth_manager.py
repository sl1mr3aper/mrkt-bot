"""Coordinates Pyrogram + MRKT JWT lifecycle.

The actual JWT handling lives inside the `amrkt.MarketClient`; this thin layer
only owns *when* to refresh and surfaces a clean async API to the rest of the
bot. It also provides a hook so background tasks can re-trigger refresh on a
fixed cadence.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from utils.logger import get_logger

log = get_logger(__name__)


class AuthManager:
    """Owns the lifecycle of the underlying `MarketClient`.

    The wrapped client is always re-authenticated via Pyrogram WebApp init data.
    """

    def __init__(self, client: Any, refresh_hours: int = 20) -> None:
        self.client = client
        self.refresh_seconds = refresh_hours * 3600
        self._last_refresh = 0.0
        self._lock = asyncio.Lock()

    async def ensure_authenticated(self) -> None:
        """Authenticate immediately if needed."""
        async with self._lock:
            await self.client.ensure_auth()
            if self._last_refresh == 0.0:
                self._last_refresh = time.time()

    async def maybe_refresh(self) -> bool:
        """Refresh token if older than `refresh_seconds`. Returns True on refresh."""
        async with self._lock:
            now = time.time()
            if now - self._last_refresh < self.refresh_seconds:
                return False
            try:
                await self.client.force_refresh()
                self._last_refresh = now
                log.info("MRKT JWT refreshed proactively")
                return True
            except Exception as exc:
                log.error("Failed to refresh MRKT JWT: {}", exc)
                return False
