"""Price history CRUD."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PriceHistory


class PriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_snapshot(
        self,
        collection: str,
        floor_price: float,
        volume_count: int,
        *,
        model: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        avg_price: float | None = None,
    ) -> PriceHistory:
        snap = PriceHistory(
            collection=collection,
            model=model,
            floor_price=floor_price,
            min_price=min_price,
            max_price=max_price,
            avg_price=avg_price,
            volume_count=volume_count,
        )
        self.session.add(snap)
        await self.session.flush()
        return snap

    async def history(
        self, collection: str, hours: int = 24
    ) -> list[PriceHistory]:
        since = datetime.now(UTC) - timedelta(hours=hours)
        result = await self.session.execute(
            select(PriceHistory)
            .where(
                PriceHistory.collection == collection,
                PriceHistory.recorded_at >= since,
            )
            .order_by(PriceHistory.recorded_at.asc())
        )
        return list(result.scalars().all())

    async def latest_floor(self, collection: str) -> float | None:
        result = await self.session.execute(
            select(PriceHistory.floor_price)
            .where(PriceHistory.collection == collection)
            .order_by(PriceHistory.recorded_at.desc())
            .limit(1)
        )
        value = result.scalar()
        return float(value) if value is not None else None
