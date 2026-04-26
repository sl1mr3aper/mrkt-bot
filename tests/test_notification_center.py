"""Tests for the NotificationCenter wrapper + repository."""

from __future__ import annotations

import asyncio
import tempfile

import pytest

from core.notification_center import NotificationCenter
from db.database import init_db
from db.repositories import NotificationRepository, UserRepository


@pytest.mark.asyncio
async def test_emit_persists_and_calls_notify() -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = init_db(f"sqlite+aiosqlite:///{tmp.name}")
    sent: list[tuple[int, str]] = []

    async def notify(tg_id: int, body: str) -> None:
        sent.append((tg_id, body))

    try:
        await db.create_all()
        async with db.session() as sess:
            user = await UserRepository(sess).get_or_create(telegram_id=42, username="x")
        center = NotificationCenter(db=db, notify=notify)
        await center.buy_filled(
            user_id=user.id,
            telegram_id=user.telegram_id,
            gift_name="Plush #100",
            collection="PlushPepe",
            price=1.5,
            target_sell=2.0,
            rarity=8.4,
        )
        await center.sold(
            user_id=user.id,
            telegram_id=user.telegram_id,
            gift_name="Plush #100",
            buy_price=1.5,
            sell_price=2.0,
            net_profit=0.45,
        )
        async with db.session() as sess:
            stored = await NotificationRepository(sess).list_by_user(user.id)
        kinds = {n.kind for n in stored}
        assert kinds == {"buy_filled", "sold"}
        # Both messages went out.
        assert len(sent) == 2
        body_blob = "\n".join(t for _, t in sent)
        assert "Plush #100" in body_blob
        assert "куплено" in body_blob.lower()
        assert "продано" in body_blob.lower()
    finally:
        await db.dispose()
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_filter_undelivered_and_mark() -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = init_db(f"sqlite+aiosqlite:///{tmp.name}")
    try:
        await db.create_all()
        async with db.session() as sess:
            user = await UserRepository(sess).get_or_create(telegram_id=7, username="z")
            repo = NotificationRepository(sess)
            n1 = await repo.add(user_id=user.id, kind="alert", title="t1", body="b1")
            n2 = await repo.add(user_id=user.id, kind="alert", title="t2", body="b2")
        async with db.session() as sess:
            repo = NotificationRepository(sess)
            undelivered = await repo.list_undelivered()
            assert {n.id for n in undelivered} >= {n1.id, n2.id}
            await repo.mark_delivered(n1.id)
        async with db.session() as sess:
            repo = NotificationRepository(sess)
            undelivered = await repo.list_undelivered()
            ids = {n.id for n in undelivered}
            assert n1.id not in ids
            assert n2.id in ids
    finally:
        await db.dispose()


@pytest.mark.asyncio
async def test_alert_and_error_helpers() -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db = init_db(f"sqlite+aiosqlite:///{tmp.name}")
    sent: list[str] = []

    async def notify(tg_id: int, body: str) -> None:
        sent.append(body)

    try:
        await db.create_all()
        async with db.session() as sess:
            user = await UserRepository(sess).get_or_create(telegram_id=99, username="u")
        center = NotificationCenter(db=db, notify=notify)
        await center.alert(
            user_id=user.id, telegram_id=user.telegram_id, title="Floor crossed!", body="..."
        )
        await center.error(
            user_id=user.id, telegram_id=user.telegram_id, title="Auth failed", body="JWT"
        )
        joined = "\n".join(sent)
        assert "Floor crossed!" in joined
        assert "Auth failed" in joined
    finally:
        await db.dispose()
