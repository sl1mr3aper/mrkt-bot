"""Builds the aiogram Dispatcher with all routers and middlewares."""

from __future__ import annotations

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from .handlers import ALL_ROUTERS
from .middlewares import LoggingMiddleware, UserMiddleware


def build_dispatcher(*, db, engine) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    # Inject runtime deps via the dispatcher workflow data.
    dp["db"] = db
    dp["engine"] = engine

    dp.update.middleware(LoggingMiddleware())
    dp.update.outer_middleware(UserMiddleware(db))

    for router in ALL_ROUTERS:
        dp.include_router(router)
    return dp
