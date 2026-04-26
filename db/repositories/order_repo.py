"""Order CRUD."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Order


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **kwargs: object) -> Order:
        order = Order(**kwargs)
        self.session.add(order)
        await self.session.flush()
        return order

    async def get(self, order_id: int) -> Order | None:
        return await self.session.get(Order, order_id)

    async def list_active(self, user_id: int) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id, Order.status == "active")
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_recent(self, user_id: int, limit: int = 50) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def find_by_gift(self, user_id: int, gift_id: str) -> Order | None:
        result = await self.session.execute(
            select(Order).where(
                Order.user_id == user_id,
                Order.gift_id == gift_id,
                Order.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def mark_filled(self, order_id: int) -> None:
        order = await self.get(order_id)
        if order:
            order.status = "filled"
            order.filled_at = datetime.now(UTC)

    async def mark_cancelled(self, order_id: int) -> None:
        order = await self.get(order_id)
        if order:
            order.status = "cancelled"
            order.cancelled_at = datetime.now(UTC)

    async def list_stuck(self, user_id: int, older_than_min: int) -> list[Order]:
        threshold = datetime.now(UTC) - timedelta(minutes=older_than_min)
        result = await self.session.execute(
            select(Order).where(
                Order.user_id == user_id,
                Order.status == "active",
                Order.created_at < threshold,
            )
        )
        return list(result.scalars().all())
