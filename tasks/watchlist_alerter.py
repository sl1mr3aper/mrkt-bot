"""Periodic checker that fires Watchlist alerts when collection floors cross
user-defined thresholds. Sends a structured notification through the
``NotificationCenter`` and updates the watchlist row's ``last_triggered``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from core.notification_center import NotificationCenter
from db.database import Database
from db.repositories import WatchlistRepository
from utils.logger import get_logger

log = get_logger(__name__)

NotifyFn = Callable[[int, str], Awaitable[None]]


class WatchlistAlerter:
    """Polls every ``interval`` seconds, fires alerts at most once per
    ``cooldown`` per item to prevent notification storms when a collection's
    floor oscillates around the threshold.
    """

    def __init__(
        self,
        engine,
        db: Database,
        notify: NotifyFn | None,
        *,
        interval_seconds: int = 600,
        cooldown_minutes: int = 30,
    ) -> None:
        self.engine = engine
        self.db = db
        self.center = NotificationCenter(db=db, notify=notify)
        self.interval = interval_seconds
        self.cooldown = timedelta(minutes=cooldown_minutes)

    async def run_forever(self) -> None:
        while True:
            try:
                await self._tick()
            except Exception as exc:  # pragma: no cover — defensive
                log.warning("watchlist alerter tick failed: {}", exc)
            await asyncio.sleep(self.interval)

    async def _tick(self) -> None:
        async with self.db.session() as sess:
            wl = await WatchlistRepository(sess).list_active()
        if not wl:
            return
        # Group by collection to avoid duplicated lookups.
        by_collection: dict[str, list] = {}
        for item in wl:
            by_collection.setdefault(item.collection, []).append(item)
        now = datetime.now(UTC)
        for collection, items in by_collection.items():
            snap = self.engine.market.collections.get(collection)
            if snap is None:
                continue
            floor = float(snap.floor_price or 0.0)
            for item in items:
                if item.last_triggered is not None and now - item.last_triggered < self.cooldown:
                    continue
                triggered = (
                    floor <= item.target_price
                    if item.direction == "below"
                    else floor >= item.target_price
                )
                if not triggered:
                    continue
                await self._fire(item, floor, now)

    async def _fire(self, item, floor: float, now: datetime) -> None:
        from db.models import User

        async with self.db.session() as sess:
            user = await sess.get(User, item.user_id)
            if user is None:
                return
            telegram_id = user.telegram_id
        await self.center.alert(
            user_id=item.user_id,
            telegram_id=telegram_id,
            title=f"🔔 Watchlist: {item.collection}",
            body=(
                f"Floor {item.collection} = <b>{floor:.3f} TON</b>\n"
                f"Цель: {'≤' if item.direction == 'below' else '≥'} "
                f"{item.target_price:.3f} TON"
            ),
        )
        async with self.db.session() as sess:
            await WatchlistRepository(sess).mark_triggered(item.id)
        log.info("watchlist alert fired: {} → {} TON", item.collection, floor)
