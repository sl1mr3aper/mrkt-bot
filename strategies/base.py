"""Base strategy abstract class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar


@dataclass
class BuyDecision:
    should_buy: bool
    reason: str = ""
    expected_profit: float = 0.0
    sell_price: float = 0.0
    rarity_score: float = 0.0
    strategy_id: int | None = None
    strategy_name: str = ""
    extras: dict[str, Any] = field(default_factory=dict)


class BaseStrategy(ABC):
    """All strategies inherit from this."""

    type_id: ClassVar[str] = "Base"
    display_name: ClassVar[str] = "Base"
    description: ClassVar[str] = ""
    default_params: ClassVar[dict[str, Any]] = {}

    def __init__(self, params: dict[str, Any] | None = None, *, analyzer: Any = None) -> None:
        merged = dict(self.default_params)
        merged.update(params or {})
        self.params = merged
        self.analyzer = analyzer
        self.id: int | None = None
        self.name: str = self.display_name

    # ─── overridable ────────────────────────────────────────

    @abstractmethod
    def should_buy(
        self,
        *,
        gift: dict[str, Any],
        analysis: Any,
        user_state: dict[str, Any],
    ) -> BuyDecision: ...

    def calculate_sell_price(
        self,
        *,
        buy_price: float,
        floor_price: float,
        fair_value: float,
        rarity_score: float,
    ) -> float:
        if self.analyzer is None:
            return round(buy_price * 1.2, 2)
        return self.analyzer.calculate_sell_price(
            buy_price=buy_price,
            floor_price=floor_price,
            fair_value=fair_value,
            rarity_score=rarity_score,
            sell_multiplier=float(self.params.get("sell_multiplier", 1.15)),
        )

    # ─── helpers ────────────────────────────────────────────

    def param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default)
