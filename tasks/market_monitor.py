"""Periodically scans market by user filters and fires strategies."""

from __future__ import annotations

import asyncio
import json
import random
from typing import Any

from sqlalchemy import select

from db.database import Database
from db.models import UserFilter
from db.repositories import StrategyRepository, UserRepository
from utils.logger import get_logger

log = get_logger(__name__)


class MarketMonitor:
    """Scans market on a randomised 20–60 s interval."""

    def __init__(
        self,
        engine: Any,
        db: Database,
        client: Any,
        *,
        min_interval: int = 20,
        max_interval: int = 60,
    ) -> None:
        self.engine = engine
        self.db = db
        self.client = client
        self.min_interval = min_interval
        self.max_interval = max_interval

    async def run_forever(self) -> None:
        while True:
            try:
                await self._iteration()
            except Exception as exc:
                log.exception("market_monitor iteration failed: {}", exc)
            await asyncio.sleep(random.uniform(self.min_interval, self.max_interval))

    async def _iteration(self) -> None:
        async with self.db.session() as sess:
            users_repo = UserRepository(sess)
            users = await users_repo.list_active_users()

        if not users:
            return

        # Refresh global state once per iteration
        await self.engine.refresh_collections()

        for user in users:
            try:
                await self._scan_user(user)
            except Exception as exc:
                log.exception("scan_user({}) failed: {}", user.id, exc)

    async def _scan_user(self, user: Any) -> None:
        await self.engine.balance.refresh()

        async with self.db.session() as sess:
            f_row = await sess.execute(
                select(UserFilter).where(
                    UserFilter.user_id == user.id, UserFilter.is_active.is_(True)
                ).limit(1)
            )
            user_filter = f_row.scalar_one_or_none()
            strategies = await StrategyRepository(sess).list_active(user.id)

        if not user_filter or not strategies:
            return

        try:
            collections = json.loads(user_filter.collection_names or "[]")
            models = json.loads(user_filter.model_names or "[]")
            backdrops = json.loads(user_filter.backdrop_names or "[]")
            symbols = json.loads(user_filter.symbol_names or "[]")
        except json.JSONDecodeError:
            collections = models = backdrops = symbols = []

        result = await self.client.search_gifts(
            collection_names=collections,
            model_names=models,
            backdrop_names=backdrops,
            symbol_names=symbols,
            min_price_ton=user_filter.min_price,
            max_price_ton=user_filter.max_price,
            ordering=user_filter.ordering or "Price",
            low_to_high=user_filter.low_to_high,
            mintable=user_filter.mintable_only or None,
            number=user_filter.number_filter,
            count=20,
        )

        active = await self.engine.strategy_runner.list_active(user.id)
        if not active:
            return

        for gift in result["items"]:
            collection = gift.get("collection") or ""
            floor = gift.get("floor_price") or self.engine.market.floor(collection)
            if floor and collection:
                self.engine.market.update_collection(collection, floor)
            analysis = self.engine.analyzer.analyse(
                gift,
                self.engine.market.listings(collection),
                floor=floor,
                sales_24h=self.engine.market.sales_24h(collection),
            )
            decisions = self.engine.strategy_runner.evaluate_all(
                gift,
                analysis,
                self.engine._user_state(user),
                active,
            )
            best = max(
                (d for d in decisions if d.should_buy),
                key=lambda d: d.expected_profit,
                default=None,
            )
            if not best:
                continue
            ok, reason = await self.engine._passes_global_checks(
                user=user, gift=gift, analysis=analysis
            )
            if not ok:
                log.debug("Skip {}: {}", gift.get("id"), reason)
                continue
            await self.engine.execute_buy(
                user=user,
                gift={**gift, "rarity_score": analysis.rarity_score},
                analysis=analysis,
                strategy_id=best.strategy_id,
                strategy_name=best.strategy_name,
            )
            # be polite — random tiny pause between user-actions
            await asyncio.sleep(random.uniform(0.5, 1.5))
