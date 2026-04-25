"""Tests for the WatchlistRepository CRUD."""

from __future__ import annotations

import asyncio
import tempfile

import pytest

from db.database import init_db
from db.repositories import UserRepository, WatchlistRepository


@pytest.mark.asyncio
async def test_add_and_list_watchlist_items() -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = init_db(f"sqlite+aiosqlite:///{tmp.name}")
    try:
        await db.create_all()
        async with db.session() as sess:
            user = await UserRepository(sess).get_or_create(telegram_id=1, username="u")
            wl = WatchlistRepository(sess)
            a = await wl.add(
                user_id=user.id,
                collection="PlushPepe",
                target_price=1.0,
                direction="below",
            )
            b = await wl.add(
                user_id=user.id,
                collection="DurovsCap",
                target_price=5.0,
                direction="above",
            )
            assert a.id != b.id
            items = await wl.list_by_user(user.id)
            assert len(items) == 2
            assert {i.collection for i in items} == {"PlushPepe", "DurovsCap"}
    finally:
        await db.dispose()
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_toggle_and_delete_watchlist_item() -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = init_db(f"sqlite+aiosqlite:///{tmp.name}")
    try:
        await db.create_all()
        async with db.session() as sess:
            user = await UserRepository(sess).get_or_create(telegram_id=1, username="u")
            wl = WatchlistRepository(sess)
            item = await wl.add(
                user_id=user.id,
                collection="Test",
                target_price=2.0,
            )
        async with db.session() as sess:
            wl = WatchlistRepository(sess)
            new_state = await wl.toggle(item.id)
            assert new_state is False
            new_state = await wl.toggle(item.id)
            assert new_state is True
        async with db.session() as sess:
            wl = WatchlistRepository(sess)
            await wl.remove(item.id)
        async with db.session() as sess:
            wl = WatchlistRepository(sess)
            assert await wl.list_by_user(user.id) == []
    finally:
        await db.dispose()


@pytest.mark.asyncio
async def test_list_active_only() -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = init_db(f"sqlite+aiosqlite:///{tmp.name}")
    try:
        await db.create_all()
        async with db.session() as sess:
            user = await UserRepository(sess).get_or_create(telegram_id=2, username="u2")
            wl = WatchlistRepository(sess)
            await wl.add(user_id=user.id, collection="X", target_price=1)
            inactive = await wl.add(user_id=user.id, collection="Y", target_price=2)
            await wl.toggle(inactive.id)  # turn off
        async with db.session() as sess:
            wl = WatchlistRepository(sess)
            active = await wl.list_active()
            assert all(i.is_active for i in active)
            assert {i.collection for i in active} == {"X"}
    finally:
        await db.dispose()
