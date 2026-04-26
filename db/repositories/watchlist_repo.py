"""CRUD for ``WatchlistItem`` entries."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WatchlistItem


class WatchlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        user_id: int,
        collection: str,
        target_price: float,
        direction: str = "below",
        note: str | None = None,
    ) -> WatchlistItem:
        item = WatchlistItem(
            user_id=user_id,
            collection=collection,
            target_price=target_price,
            direction=direction,
            note=note,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def list_by_user(self, user_id: int) -> list[WatchlistItem]:
        result = await self.session.execute(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active(self) -> list[WatchlistItem]:
        result = await self.session.execute(
            select(WatchlistItem).where(WatchlistItem.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def get(self, item_id: int) -> WatchlistItem | None:
        return await self.session.get(WatchlistItem, item_id)

    async def remove(self, item_id: int) -> None:
        item = await self.get(item_id)
        if item:
            await self.session.delete(item)

    async def toggle(self, item_id: int) -> bool:
        item = await self.get(item_id)
        if not item:
            return False
        item.is_active = not item.is_active
        return item.is_active

    async def mark_triggered(self, item_id: int) -> None:
        item = await self.get(item_id)
        if item:
            item.last_triggered = datetime.now(UTC)
