"""Periodic light-weight health probe — pings API and balance."""

from __future__ import annotations

import asyncio
from typing import Any

from utils.logger import get_logger

log = get_logger(__name__)


class HealthChecker:
    def __init__(self, engine: Any, *, interval_seconds: int = 300) -> None:
        self.engine = engine
        self.interval = interval_seconds

    async def run_forever(self) -> None:
        while True:
            try:
                await self.engine.balance.refresh(force=True)
                log.debug("health ok — balance {} TON", self.engine.market.balance_ton)
            except Exception as exc:
                log.warning("health probe failed: {}", exc)
            await asyncio.sleep(self.interval)
