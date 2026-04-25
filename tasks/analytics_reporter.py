"""Daily analytics digest sender."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, time, timedelta
from typing import Any

from analytics.reports import daily_report
from db.database import Database
from db.repositories import (
    PortfolioRepository,
    StrategyRepository,
    TradeRepository,
    UserRepository,
)
from utils.logger import get_logger

log = get_logger(__name__)


class AnalyticsReporter:
    def __init__(self, engine: Any, db: Database, *, notify: Any, hour_utc: int = 21) -> None:
        self.engine = engine
        self.db = db
        self.notify = notify
        self.hour_utc = hour_utc

    async def run_forever(self) -> None:
        while True:
            await asyncio.sleep(self._seconds_until_next_run())
            try:
                await self._send_all()
            except Exception as exc:
                log.warning("analytics_reporter: {}", exc)

    def _seconds_until_next_run(self) -> float:
        now = datetime.now(UTC)
        target = datetime.combine(now.date(), time(self.hour_utc, 0, tzinfo=UTC))
        if target <= now:
            target += timedelta(days=1)
        return max(60.0, (target - now).total_seconds())

    async def _send_all(self) -> None:
        async with self.db.session() as sess:
            users = await UserRepository(sess).list_active_users()
        for user in users:
            await self._send_for_user(user)

    async def _send_for_user(self, user: Any) -> None:
        async with self.db.session() as sess:
            stats = await TradeRepository(sess).daily_stats(user.id)
            all_time = await TradeRepository(sess).all_time_profit(user.id)
            top = await TradeRepository(sess).top_gainers(user.id, days=1, limit=1)
            bottom = await TradeRepository(sess).top_losers(user.id, days=1, limit=1)
            portfolio = await PortfolioRepository(sess).list_by_user(user.id)
            strategies = await StrategyRepository(sess).list_active(user.id)

        portfolio_value = sum((p.target_sell or p.buy_price) for p in portfolio)
        await self.notify(
            user.telegram_id,
            daily_report(
                date=datetime.now(UTC),
                daily_profit=stats["net"],
                all_time_profit=all_time,
                balance=self.engine.market.balance_ton,
                total_trades=stats["count"],
                profitable=self.engine.profit.stats.daily_profitable,
                breakeven=self.engine.profit.stats.daily_breakeven,
                losing=self.engine.profit.stats.daily_losing,
                stop_losses=self.engine.profit.stats.daily_stop_losses,
                best_trade_text=(
                    f"{top[0].gift_name}: +{top[0].profit_pct:.1f}%" if top else None
                ),
                worst_trade_text=(
                    f"{bottom[0].gift_name}: {bottom[0].profit_pct:.1f}%"
                    if bottom
                    else None
                ),
                portfolio_size=len(portfolio),
                portfolio_value=round(portfolio_value, 2),
                active_strategies=len(strategies),
            ),
        )
