"""Continuously enforces stop-losses for every active user."""

from __future__ import annotations

import asyncio
from typing import Any

from db.database import Database
from db.repositories import UserRepository
from utils.logger import get_logger

log = get_logger(__name__)


class StopLossMonitor:
    def __init__(self, engine: Any, db: Database, interval_seconds: int = 60) -> None:
        self.engine = engine
        self.db = db
        self.interval = interval_seconds

    async def run_forever(self) -> None:
        while True:
            try:
                async with self.db.session() as sess:
                    users = await UserRepository(sess).list_active_users()
                for user in users:
                    await self.engine.enforce_stop_loss_for_user(user)
            except Exception as exc:
                log.warning("stop_loss_monitor: {}", exc)
            await asyncio.sleep(self.interval)
