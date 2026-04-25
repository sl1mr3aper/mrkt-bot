"""CRUD for queued ``Notification`` entries."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Notification


class NotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        user_id: int,
        kind: str,
        title: str,
        body: str,
    ) -> Notification:
        n = Notification(user_id=user_id, kind=kind, title=title, body=body)
        self.session.add(n)
        await self.session.flush()
        return n

    async def list_undelivered(self, limit: int = 50) -> list[Notification]:
        result = await self.session.execute(
            select(Notification)
            .where(Notification.delivered.is_(False))
            .order_by(Notification.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: int,
        *,
        limit: int = 50,
        kind: str | None = None,
    ) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if kind:
            stmt = stmt.where(Notification.kind == kind)
        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_delivered(self, notification_id: int) -> None:
        n = await self.session.get(Notification, notification_id)
        if n:
            n.delivered = True
            n.delivered_at = datetime.now(UTC)

    async def purge_delivered(self, *, older_than_days: int = 30) -> int:
        from sqlalchemy import delete

        cutoff = datetime.now(UTC).replace(microsecond=0)
        cutoff = cutoff.replace(day=max(1, cutoff.day - older_than_days))
        stmt = delete(Notification).where(
            Notification.delivered.is_(True),
            Notification.created_at < cutoff,
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
