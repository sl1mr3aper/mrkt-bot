"""UndervalueHunter — gifts with rare model priced as common."""

from __future__ import annotations

from typing import Any

from .base import BaseStrategy, BuyDecision


class UndervalueHunterStrategy(BaseStrategy):
    type_id = "UndervalueHunter"
    display_name = "UndervalueHunter"
    description = "Ищем редкие модели проданные как common."
    default_params = {
        "min_value_ratio": 1.5,
        "max_model_pct": 5.0,
        "max_buy_ton": 5.0,
        "min_rarity_score": 5.0,
        "min_profit_ton": 0.10,
    }

    def should_buy(
        self,
        *,
        gift: dict[str, Any],
        analysis: Any,
        user_state: dict[str, Any],
    ) -> BuyDecision:
        price = float(gift.get("price") or 0.0)
        fair = analysis.fair_value
        if fair <= 0 or price <= 0:
            return BuyDecision(False, "no fair / price")
        model_pct = float(gift.get("modelRarity") or 100.0)
        if model_pct > float(self.params["max_model_pct"]):
            return BuyDecision(False, f"Model {model_pct}% не редкая")
        if analysis.rarity_score < float(self.params["min_rarity_score"]):
            return BuyDecision(False, "rarity слишком низкая")
        ratio = fair / price if price else 0
        if ratio < float(self.params["min_value_ratio"]):
            return BuyDecision(False, f"value ratio {ratio:.2f} < min")
        if price > float(self.params["max_buy_ton"]):
            return BuyDecision(False, "price > max_buy_ton")

        commission = price * float(user_state.get("commission", 0.05))
        sell_at = fair * 0.80
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
