"""Portfolio (gifts owned, awaiting sale)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PortfolioItem


class PortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, **kwargs: object) -> PortfolioItem:
        item = PortfolioItem(**kwargs)
        self.session.add(item)
        await self.session.flush()
        return item

    async def get(self, gift_id: str) -> PortfolioItem | None:
        result = await self.session.execute(
            select(PortfolioItem).where(PortfolioItem.gift_id == gift_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> list[PortfolioItem]:
        result = await self.session.execute(
            select(PortfolioItem)
            .where(PortfolioItem.user_id == user_id)
            .order_by(PortfolioItem.bought_at.desc())
        )
        return list(result.scalars().all())

    async def remove(self, gift_id: str) -> None:
        item = await self.get(gift_id)
        if item:
            await self.session.delete(item)

    async def update_listing(self, gift_id: str, sell_price: float, listed_at: object) -> None:
        item = await self.get(gift_id)
        if item:
            item.target_sell = sell_price
            item.listed_at = listed_at  # type: ignore[assignment]
