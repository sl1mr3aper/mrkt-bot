"""FloorSniper — instant buy if listing is below current floor."""

from __future__ import annotations

from typing import Any

from .base import BaseStrategy, BuyDecision


class FloorSniperStrategy(BaseStrategy):
    type_id = "FloorSniper"
    display_name = "FloorSniper"
    description = "Снайпит листинги ниже floor."
    default_params = {
        "below_floor_pct": 3.0,
        "instant_buy": True,
        "max_daily_buys": 20,
        "max_per_buy_ton": 3.0,
        "sell_at_floor_premium": 0.03,  # +3% to floor
        "min_profit_ton": 0.02,
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
        if floor <= 0:
            return BuyDecision(False, "no floor")

        threshold = floor * (1 - float(self.params["below_floor_pct"]) / 100.0)
        if price > threshold:
            return BuyDecision(False, f"price {price} > threshold {threshold:.2f}")
        if price > float(self.params["max_per_buy_ton"]):
            return BuyDecision(False, "price > max_per_buy_ton")
        if user_state.get("daily_buys", 0) >= int(self.params["max_daily_buys"]):
            return BuyDecision(False, "Достигнут дневной лимит снайпа")

        sell_at = floor * (1 + float(self.params["sell_at_floor_premium"]))
        commission = price * float(user_state.get("commission", 0.05))
        net = sell_at - price - commission
        if net < float(self.params["min_profit_ton"]):
            return BuyDecision(False, "net < min_profit")
        return BuyDecision(
            True,
            "ok",
            expected_profit=round(net, 4),
            sell_price=round(sell_at, 2),
            rarity_score=analysis.rarity_score,
        )
