"""RaritySniper — buys rare gifts undervalued vs fair value."""

from __future__ import annotations

from typing import Any

from .base import BaseStrategy, BuyDecision


class RaritySniperStrategy(BaseStrategy):
    type_id = "RaritySniper"
    display_name = "RaritySniper"
    description = "Покупаем редкие подарки дёшево, продаём по fair value."
    default_params = {
        "min_rarity_score": 6.0,
        "max_price_vs_fair": 0.60,
        "target_profit_pct": 40.0,
        "max_buy_ton": 15.0,
        "max_hold_hours": 48,
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
        score = analysis.rarity_score
        fair = analysis.fair_value
        if fair <= 0:
            return BuyDecision(False, "Нет fair value")
        if score < float(self.params["min_rarity_score"]):
            return BuyDecision(False, f"score {score:.1f} < min_rarity")
        ratio = price / fair if fair > 0 else 1
        if ratio > float(self.params["max_price_vs_fair"]):
            return BuyDecision(False, f"price/fair {ratio:.2f} > max_price_vs_fair")
        if price > float(self.params["max_buy_ton"]):
            return BuyDecision(False, "price > max_buy_ton")

        commission = price * float(user_state.get("commission", 0.05))
        sell_at = fair * 0.75
        net = sell_at - price - commission
        if net < float(self.params["min_profit_ton"]):
            return BuyDecision(False, f"net {net:.4f} < min_profit")
        return BuyDecision(
            True,
            "ok",
            expected_profit=round(net, 4),
            sell_price=round(sell_at, 2),
            rarity_score=score,
        )
