"""Trade history CRUD + aggregations."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Trade


class TradeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, **kwargs: object) -> Trade:
        trade = Trade(**kwargs)
        self.session.add(trade)
        await self.session.flush()
        return trade

    async def list_by_user(
        self, user_id: int, limit: int = 100
    ) -> list[Trade]:
        result = await self.session.execute(
            select(Trade)
            .where(Trade.user_id == user_id)
            .order_by(Trade.sold_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def daily_stats(self, user_id: int, days: int = 1) -> dict[str, float]:
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            select(
                func.count(Trade.id),
                func.coalesce(func.sum(Trade.net_profit), 0.0),
                func.coalesce(func.sum(Trade.gross_profit), 0.0),
            ).where(Trade.user_id == user_id, Trade.sold_at >= since)
        )
        count, net, gross = result.one()
        return {"count": int(count or 0), "net": float(net or 0), "gross": float(gross or 0)}

    async def all_time_profit(self, user_id: int) -> float:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Trade.net_profit), 0.0)).where(
                Trade.user_id == user_id
            )
        )
        return float(result.scalar() or 0)

    async def top_gainers(self, user_id: int, days: int, limit: int = 5) -> list[Trade]:
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            select(Trade)
            .where(Trade.user_id == user_id, Trade.sold_at >= since)
            .order_by(Trade.profit_pct.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def top_losers(self, user_id: int, days: int, limit: int = 5) -> list[Trade]:
        since = datetime.now(UTC) - timedelta(days=days)
        result = await self.session.execute(
            select(Trade)
            .where(Trade.user_id == user_id, Trade.sold_at >= since)
            .order_by(Trade.profit_pct.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
