"""Watches active orders, settles fills, sends stuck-order notifications."""

from __future__ import annotations

import asyncio
import random
from datetime import UTC, datetime
from typing import Any

from db.database import Database
from db.repositories import (
    OrderRepository,
    PortfolioRepository,
    UserRepository,
)
from utils.formatters import fmt_stuck_order
from utils.logger import get_logger

log = get_logger(__name__)


class OrderWatcher:
    """Polls API + DB for changes; settles trades on fill."""

    def __init__(
        self,
        engine: Any,
        db: Database,
        client: Any,
        *,
        notify: Any,
        poll_seconds: int = 30,
        stuck_minutes: int = 5,
    ) -> None:
        self.engine = engine
        self.db = db
        self.client = client
        self.notify = notify
        self.poll_seconds = poll_seconds
        self.stuck_minutes = stuck_minutes
        self._notified_stuck: set[int] = set()

    async def run_forever(self) -> None:
        while True:
            try:
                await self._iteration()
            except Exception as exc:
                log.exception("order_watcher: {}", exc)
            await asyncio.sleep(
                self.poll_seconds + random.uniform(-2.0, 2.0)
            )

    async def _iteration(self) -> None:
        async with self.db.session() as sess:
            users = await UserRepository(sess).list_active_users()

        for user in users:
            try:
                await self._reconcile_user(user)
            except Exception as exc:
                log.exception("reconcile {}: {}", user.id, exc)

    async def _reconcile_user(self, user: Any) -> None:
        async with self.db.session() as sess:
            order_repo = OrderRepository(sess)
            portfolio_repo = PortfolioRepository(sess)
            active_orders = await order_repo.list_active(user.id)
            stuck = await order_repo.list_stuck(user.id, self.stuck_minutes)

        # Inventory check — a buy order is settled when gift appears in
        # inventory; a sell order is settled when gift disappears.
        if user.dry_run:
            return

        try:
            inventory = await self.client.get_inventory(count=200)
        except Exception as exc:
            log.warning("get_inventory failed: {}", exc)
            return

        owned_ids = {item.get("id") for item in inventory if item.get("id")}

        for order in active_orders:
            if order.dry_run:
                continue
            if order.order_type == "buy" and order.gift_id in owned_ids:
                await self.engine.orders.mark_filled(order.id)
            elif order.order_type == "sell" and order.gift_id and order.gift_id not in owned_ids:
                await self.engine.settle_sale(
                    user=user, gift_id=order.gift_id, sell_price=order.price
                )
                await self.engine.orders.mark_filled(order.id)

        # Stuck orders → notify once
        for order in stuck:
            if order.id in self._notified_stuck:
                continue
            self._notified_stuck.add(order.id)
            current_floor = self.engine.market.floor(order.collection or "")
            above_pct = (
                ((order.price - current_floor) / current_floor * 100.0)
                if current_floor
                else 0.0
            )
            await self.notify(
                user.telegram_id,
                fmt_stuck_order({
                    "gift_name": order.gift_name,
                    "sell_price": order.price,
                    "current_floor": current_floor,
                    "above_floor_pct": above_pct,
                    "age_min": int((datetime.now(UTC) - (
                        order.created_at if order.created_at.tzinfo else order.created_at.replace(tzinfo=UTC)
                    )).total_seconds() / 60),
                }),
            )

        # Listing portfolio items whose cooldown finished
        async with self.db.session() as sess:
            owned = await PortfolioRepository(sess).list_by_user(user.id)
        for item in owned:
            if item.listed_at is not None:
                continue
            cooldown_until = item.cooldown_until
            if cooldown_until and cooldown_until.tzinfo is None:
                cooldown_until = cooldown_until.replace(tzinfo=UTC)
            if cooldown_until and cooldown_until > datetime.now(UTC):
                continue
            if item.target_sell:
                await self.engine.list_for_sale_after_cooldown(
                    user=user,
                    gift_id=item.gift_id,
                    sell_price=item.target_sell,
                )
