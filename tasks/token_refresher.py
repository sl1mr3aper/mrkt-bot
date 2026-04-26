"""Periodic JWT refresh."""

from __future__ import annotations

import asyncio

from core.auth_manager import AuthManager
from utils.logger import get_logger

log = get_logger(__name__)


class TokenRefresher:
    def __init__(self, auth: AuthManager, interval_hours: int = 20) -> None:
        self.auth = auth
        self.interval = interval_hours * 3600

    async def run_forever(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            try:
                await self.auth.maybe_refresh()
            except Exception as exc:
                log.warning("token refresh failed: {}", exc)
