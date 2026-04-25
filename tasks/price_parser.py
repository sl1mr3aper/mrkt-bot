"""Saves price snapshots for charts and analytics."""

from __future__ import annotations

import asyncio
from typing import Any

from db.database import Database
from utils.logger import get_logger

log = get_logger(__name__)


class PriceParser:
    def __init__(self, engine: Any, db: Database, interval_minutes: int = 30) -> None:
        self.engine = engine
        self.db = db
        self.interval_minutes = interval_minutes

    async def run_forever(self) -> None:
        while True:
            try:
                collections = await self.engine.refresh_collections()
                for c in collections:
                    await self.engine.record_price_snapshot(c["name"])
            except Exception as exc:
                log.warning("price_parser failed: {}", exc)
            await asyncio.sleep(self.interval_minutes * 60)
