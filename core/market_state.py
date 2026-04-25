"""In-memory snapshot of the market — caches floors, listings, balance."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CollectionSnapshot:
    name: str
    title: str = ""
    floor_price: float = 0.0
    previous_floor: float = 0.0
    volume: int = 0
    listings: list[dict[str, Any]] = field(default_factory=list)
    sales_24h: int = 0
    updated_at: float = field(default_factory=time.time)


class MarketState:
    """Single source of truth for live market data within a process."""

    def __init__(self) -> None:
        self.collections: dict[str, CollectionSnapshot] = {}
        self.balance_ton: float = 0.0
        self.user_id: int | None = None
        self.daily_buys: int = 0
        self.daily_loss: float = 0.0
        self.last_balance_update: float = 0.0
        self._sales_velocity: dict[str, list[float]] = defaultdict(list)

    # ─── floor / listings ─────────────────────────────────

    def update_collection(
        self,
        name: str,
        floor_price: float,
        volume: int = 0,
        listings: list[dict[str, Any]] | None = None,
        *,
        title: str | None = None,
    ) -> None:
        snap = self.collections.setdefault(name, CollectionSnapshot(name=name))
        if snap.floor_price and snap.floor_price != floor_price:
            snap.previous_floor = snap.floor_price
        elif not snap.previous_floor:
            snap.previous_floor = floor_price
        snap.floor_price = floor_price
        if title and not snap.title:
            snap.title = title
        if volume:
            snap.volume = volume
        if listings is not None:
            snap.listings = listings
        snap.updated_at = time.time()

    def floor(self, collection: str) -> float:
        snap = self.collections.get(collection)
        return snap.floor_price if snap else 0.0

    def listings(self, collection: str) -> list[dict[str, Any]]:
        snap = self.collections.get(collection)
        return snap.listings if snap else []

    # ─── balance ──────────────────────────────────────────

    def set_balance(self, balance_ton: float) -> None:
        self.balance_ton = round(balance_ton, 4)
        self.last_balance_update = time.time()

    def has_balance_for(self, price: float, *, buffer: float = 0.15) -> bool:
        return self.balance_ton >= price * (1 + buffer)

    # ─── velocity tracking ────────────────────────────────

    def record_sale(self, collection: str) -> None:
        bucket = self._sales_velocity[collection]
        now = time.time()
        bucket.append(now)
        cutoff = now - 24 * 3600
        self._sales_velocity[collection] = [t for t in bucket if t >= cutoff]
        snap = self.collections.get(collection)
        if snap:
            snap.sales_24h = len(self._sales_velocity[collection])

    def sales_24h(self, collection: str) -> int:
        return len(self._sales_velocity.get(collection, []))

    # ─── daily counters ───────────────────────────────────

    def increment_daily_buys(self) -> None:
        self.daily_buys += 1

    def add_daily_loss(self, value: float) -> None:
        self.daily_loss = round(self.daily_loss + value, 4)

    def reset_daily(self) -> None:
        self.daily_buys = 0
        self.daily_loss = 0.0
