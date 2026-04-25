"""Stop-loss engine — triggers urgent sell when floor drops."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any


class StopLossAction(str, Enum):
    HOLD = "HOLD"
    CONSIDER_SELL = "CONSIDER_SELL"
    SELL_NOW = "SELL_NOW"


@dataclass
class StopLossDecision:
    action: StopLossAction
    sell_at: float = 0.0
    reason: str = ""
    stop_threshold: float = 0.0
    floor_change_pct: float = 0.0


class StopLossEngine:
    """Algorithm 4.4 — triggers urgent sell on big floor drops."""

    def __init__(
        self,
        *,
        commission: float = 0.05,
        consider_sell_after_hours: int = 2,
        max_loss_pct: float = 10.0,
    ) -> None:
        self.commission = commission
        self.consider_after_hours = consider_sell_after_hours
        self.max_loss_pct = max_loss_pct

    def evaluate(
        self,
        *,
        buy_price: float,
        current_floor: float,
        bought_at: datetime,
        stop_loss_pct: float,
        now: datetime | None = None,
    ) -> StopLossDecision:
        now = now or datetime.now(UTC)
        if buy_price <= 0:
            return StopLossDecision(StopLossAction.HOLD, reason="zero buy price")

        stop_threshold = buy_price * (1 - stop_loss_pct / 100.0)
        min_break_even = buy_price * (1 + self.commission)
        floor_change_pct = (current_floor - buy_price) / buy_price * 100.0 if buy_price else 0.0

        if current_floor <= stop_threshold:
            sell_at = max(current_floor, buy_price * (1 - self.max_loss_pct / 100.0))
            return StopLossDecision(
                action=StopLossAction.SELL_NOW,
                sell_at=round(sell_at, 2),
                stop_threshold=round(stop_threshold, 2),
                floor_change_pct=round(floor_change_pct, 2),
                reason="floor below stop threshold",
            )

        if bought_at.tzinfo is None:
            bought_at = bought_at.replace(tzinfo=UTC)
        age = now - bought_at
        if (
            current_floor < min_break_even
            and age >= timedelta(hours=self.consider_after_hours)
        ):
            return StopLossDecision(
                action=StopLossAction.CONSIDER_SELL,
                sell_at=round(current_floor, 2),
                stop_threshold=round(stop_threshold, 2),
                floor_change_pct=round(floor_change_pct, 2),
                reason="floor below break-even for too long",
            )

        return StopLossDecision(
            action=StopLossAction.HOLD,
            stop_threshold=round(stop_threshold, 2),
            floor_change_pct=round(floor_change_pct, 2),
            reason="floor above threshold",
        )

    @staticmethod
    def stop_loss_price(buy_price: float, stop_loss_pct: float) -> float:
        return round(buy_price * (1 - stop_loss_pct / 100.0), 2)

    @staticmethod
    def gift_age_seconds(item: Any) -> int:
        bought_at = getattr(item, "bought_at", None)
        if bought_at is None:
            return 0
        if bought_at.tzinfo is None:
            bought_at = bought_at.replace(tzinfo=UTC)
        return int((datetime.now(UTC) - bought_at).total_seconds())
