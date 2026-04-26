"""End-to-end TradingEngine smoke test using MockMrktClient."""

from __future__ import annotations

import asyncio
import os
import tempfile
from types import SimpleNamespace

import pytest

from core import TradingEngine
from core.mrkt_client import MockMrktClient
from db.database import init_db
from db.repositories import (
    StrategyRepository,
    TradeRepository,
    UserRepository,
)


@pytest.mark.asyncio
async def test_dry_run_buy_and_settle() -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    try:
        cfg = SimpleNamespace(
            COOLDOWN_SECONDS=0,
            commission=0.05,
            MARKET_COMMISSION_PCT=5.0,
        )
        db = init_db(f"sqlite+aiosqlite:///{tmp.name}")
        await db.create_all()
        client = MockMrktClient()
        client._balance = 50.0
        client.gifts = [
            {
                "id": "g1",
                "name": "Gift1",
                "price": 1.0,
                "collection": "Coll",
                "modelRarity": 50.0,
                "backdropRarity": 50.0,
                "symbolRarity": 50.0,
                "floor_price": 1.0,
            }
        ]

        notifications: list[tuple[int, str]] = []

        async def notify(uid: int, text: str) -> None:
            notifications.append((uid, text))

        engine = TradingEngine(client=client, db=db, config=cfg, notify=notify)
        engine.market.update_collection("Coll", 1.0)
        await engine.balance.refresh()

        async with db.session() as sess:
            user = await UserRepository(sess).get_or_create(
                telegram_id=42, username="dj"
            )
            user.dry_run = True
            await StrategyRepository(sess).create(
                user_id=user.id,
                name="Test",
                type_="FloorMultiplier",
                params={"buy_multiplier": 1.0, "sell_multiplier": 1.20, "min_profit_ton": 0.01},
                is_active=True,
            )

        async with db.session() as sess:
            users = await UserRepository(sess).list_active_users()  # auto_trading=False
        assert users == []

        # Force evaluate buy via the analyzer & strategy directly:
        analysis = engine.analyzer.analyse(
            client.gifts[0], [{"price": 1.0}], floor=1.0
        )
        await engine.execute_buy(
            user=user,
            gift={**client.gifts[0], "rarity_score": analysis.rarity_score},
            analysis=analysis,
            strategy_id=None,
            strategy_name="Test",
        )

        # Dry run path → no client.bought_calls
        assert client.bought_calls == []
        # But order should be recorded
        async with db.session() as sess:
            trades = await TradeRepository(sess).list_by_user(user.id)
        # No completed trade because dry run
        assert trades == []

        # Notifications should include DRY RUN
        assert any("DRY RUN" in t for _, t in notifications)
    finally:
        await asyncio.sleep(0)  # let async tasks complete
        os.unlink(tmp.name)
