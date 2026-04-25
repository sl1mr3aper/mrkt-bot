"""Async SQLAlchemy engine + session management."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from utils.logger import get_logger

log = get_logger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class Database:
    """Wraps engine + session factory; can create tables / dispose."""

    def __init__(self, url: str) -> None:
        self.url = url
        self.engine = create_async_engine(url, future=True, echo=False)
        self.session_factory = async_sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def create_all(self) -> None:
        # ensure parent dir exists for sqlite file
        if self.url.startswith("sqlite"):
            db_path = self.url.split("///", 1)[-1]
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Import models so they register with metadata
        from . import models  # noqa: F401

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("Database initialised at {}", self.url)

    async def dispose(self) -> None:
        await self.engine.dispose()
        log.info("Database engine disposed")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as sess:
            try:
                yield sess
                await sess.commit()
            except Exception:
                await sess.rollback()
                raise


_db: Database | None = None


def init_db(url: str) -> Database:
    """Initialise the global DB singleton."""
    global _db
    _db = Database(url)
    return _db


def get_db() -> Database:
    """Return previously-initialised DB."""
    if _db is None:
        raise RuntimeError("Database not initialised — call init_db() first")
    return _db
