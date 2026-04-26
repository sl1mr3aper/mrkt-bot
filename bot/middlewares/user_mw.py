"""Loads/creates User in DB and injects into handler kwargs as `user`."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from db.database import Database
from db.repositories import UserRepository


class UserMiddleware(BaseMiddleware):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user is not None:
            async with self.db.session() as sess:
                repo = UserRepository(sess)
                user = await repo.get_or_create(
                    telegram_id=tg_user.id, username=tg_user.username
                )
                # Detach from session so handlers can use it freely.
                await sess.refresh(user)
            data["user"] = user
        return await handler(event, data)
