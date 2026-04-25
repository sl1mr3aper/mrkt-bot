"""Logs every update; catches and reports unhandled exceptions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from utils.logger import get_logger

log = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        kind = type(event).__name__
        user = data.get("event_from_user")
        uid = user.id if user else None
        try:
            log.debug("[{}][user={}] {}", kind, uid, getattr(event, "data", None) or getattr(event, "text", None))
            return await handler(event, data)
        except Exception as exc:
            log.exception("Update handler crashed: {}", exc)
            raise
