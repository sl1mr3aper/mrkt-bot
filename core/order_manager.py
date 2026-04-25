"""Active order bookkeeping + reconciliation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from db.database import Database
from db.repositories import OrderRepository, PortfolioRepository
from utils.logger import get_logger

log = get_logger(__name__)


class OrderManager:
    """High-level order lifecycle (create / fill / cancel) backed by DB."""

    def __init__(self, db: Database) -> None:
        self.db = db

    async def record_buy(
        self,
        *,
        user_id: int,
        strategy_id: int | None,
        gift: dict[str, Any],
        price: float,
        target_price: float | None,
        dry_run: bool,
    ) -> int:
        async with self.db.session() as sess:
            repo = OrderRepository(sess)
            order = await repo.create(
                user_id=user_id,
                strategy_id=strategy_id,
                order_type="buy",
                gift_id=gift.get("id"),
                gift_name=gift.get("name") or gift.get("title"),
                collection=gift.get("collection"),
                model=gift.get("model"),
                backdrop=gift.get("backdrop"),
                symbol=gift.get("symbol"),
                model_rarity=gift.get("modelRarity"),
                backdrop_rarity=gift.get("backdropRarity"),
                symbol_rarity=gift.get("symbolRarity"),
                rarity_score=gift.get("rarity_score"),
                number=gift.get("number"),
                price=price,
                target_price=target_price,
                status="filled" if not dry_run else "active",
                dry_run=dry_run,
                filled_at=datetime.now(UTC) if not dry_run else None,
            )
            return int(order.id)

    async def record_sell(
        self,
        *,
        user_id: int,
        gift: dict[str, Any],
        price: float,
        strategy_id: int | None,
        dry_run: bool,
    ) -> int:
        async with self.db.session() as sess:
            repo = OrderRepository(sess)
            order = await repo.create(
                user_id=user_id,
                strategy_id=strategy_id,
                order_type="sell",
                gift_id=gift.get("id"),
                gift_name=gift.get("name") or gift.get("title"),
                collection=gift.get("collection"),
                model=gift.get("model"),
                backdrop=gift.get("backdrop"),
                symbol=gift.get("symbol"),
                rarity_score=gift.get("rarity_score"),
                number=gift.get("number"),
                price=price,
                status="active",
                dry_run=dry_run,
            )
            return int(order.id)

    async def mark_filled(self, order_id: int) -> None:
        async with self.db.session() as sess:
            await OrderRepository(sess).mark_filled(order_id)

    async def cancel(self, order_id: int) -> None:
        async with self.db.session() as sess:
            await OrderRepository(sess).mark_cancelled(order_id)

    async def list_active(self, user_id: int) -> list[Any]:
        async with self.db.session() as sess:
            return await OrderRepository(sess).list_active(user_id)

    async def find_active_by_gift(self, user_id: int, gift_id: str) -> Any | None:
        async with self.db.session() as sess:
            return await OrderRepository(sess).find_by_gift(user_id, gift_id)

    async def list_stuck(self, user_id: int, older_than_min: int) -> list[Any]:
        async with self.db.session() as sess:
            return await OrderRepository(sess).list_stuck(user_id, older_than_min)

    async def is_in_flight(self, user_id: int, gift_id: str) -> bool:
        """True if gift has an active order or sits in portfolio."""
        async with self.db.session() as sess:
            order = await OrderRepository(sess).find_by_gift(user_id, gift_id)
            if order is not None:
                return True
            owned = await PortfolioRepository(sess).get(gift_id)
            return owned is not None
