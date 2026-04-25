"""User CRUD."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, UserFilter


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self, telegram_id: int, username: str | None = None
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            if username and user.username != username:
                user.username = username
            return user
        user = User(telegram_id=telegram_id, username=username)
        self.session.add(user)
        await self.session.flush()
        # initial empty filter
        f = UserFilter(user_id=user.id)
        self.session.add(f)
        await self.session.flush()
        return user

    async def update_settings(self, user_id: int, **kwargs: object) -> None:
        user = await self.session.get(User, user_id)
        if not user:
            return
        allowed = {
            "dry_run", "stop_loss_pct", "max_buy_ton", "min_profit_ton",
            "large_deal_ton", "max_daily_loss_ton", "max_daily_trades",
            "proxy_url", "auto_trading",
        }
        for key, value in kwargs.items():
            if key in allowed:
                setattr(user, key, value)

    async def set_notifications(self, user_id: int, notifications: dict[str, bool]) -> None:
        user = await self.session.get(User, user_id)
        if user:
            user.notifications = json.dumps(notifications)

    async def get_notifications(self, user_id: int) -> dict[str, bool]:
        user = await self.session.get(User, user_id)
        if not user:
            return {}
        try:
            return json.loads(user.notifications or "{}")
        except json.JSONDecodeError:
            return {}

    async def list_active_users(self) -> list[User]:
        result = await self.session.execute(
            select(User).where(User.auto_trading.is_(True))
        )
        return list(result.scalars().all())
