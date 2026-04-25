"""FloorMultiplier strategy — buy on floor, sell at floor * X%."""

from __future__ import annotations

from typing import Any

from .base import BaseStrategy, BuyDecision


class FloorMultiplierStrategy(BaseStrategy):
    type_id = "FloorMultiplier"
    display_name = "FloorMultiplier"
    description = "Стабильный доход: покупка по floor, продажа +10–25%."
    default_params = {
        "buy_multiplier": 1.0,
        "sell_multiplier": 1.15,
        "min_profit_ton": 0.05,
        "max_position_ton": 10.0,
        "max_positions": 5,
    }

    def should_buy(
        self,
        *,
        gift: dict[str, Any],
        analysis: Any,
        user_state: dict[str, Any],
    ) -> BuyDecision:
        price = float(gift.get("price") or 0.0)
        floor = analysis.floor or analysis.real_floor or 0.0
        max_buy = floor * float(self.params["buy_multiplier"])
        if floor <= 0:
            return BuyDecision(False, "Нет floor для коллекции")
        if price > max_buy:
            return BuyDecision(False, f"Цена {price} > floor*{self.params['buy_multiplier']}")
        sell_at = floor * float(self.params["sell_multiplier"])
        commission = price * float(user_state.get("commission", 0.05))
        net = sell_at - price - commission
        if net < float(self.params["min_profit_ton"]):
            return BuyDecision(False, f"Прибыль {net:.4f} < min_profit")
        if price > float(self.params["max_position_ton"]):
            return BuyDecision(False, "Цена > max_position_ton")
        return BuyDecision(
            True,
            "ok",
            expected_profit=round(net, 4),
            sell_price=round(sell_at, 2),
            rarity_score=analysis.rarity_score,
        )
