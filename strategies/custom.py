"""Custom user-defined strategy — purely declarative rules."""

from __future__ import annotations

from typing import Any

from .base import BaseStrategy, BuyDecision


class CustomStrategy(BaseStrategy):
    """Generic strategy configurable via params (no python eval).

    Supported params (all optional)::

        {
            "max_price_ton": 5.0,
            "min_rarity_score": 5.0,
            "max_model_pct": null,
            "min_value_ratio": 1.0,           # fair / price
            "buy_multiplier": null,           # floor * X
            "sell_multiplier": 1.20,
            "max_number": null,
            "min_profit_ton": 0.05,
        }
    """

    type_id = "Custom"
    display_name = "Custom"
    description = "Кастомные условия покупки/продажи."
    default_params = {
        "max_price_ton": None,
        "min_rarity_score": None,
        "max_model_pct": None,
        "min_value_ratio": None,
        "buy_multiplier": None,
        "sell_multiplier": 1.20,
        "max_number": None,
        "min_profit_ton": 0.05,
    }

    def should_buy(
        self,
        *,
        gift: dict[str, Any],
        analysis: Any,
        user_state: dict[str, Any],
    ) -> BuyDecision:
        price = float(gift.get("price") or 0.0)
        if price <= 0:
            return BuyDecision(False, "no price")

        max_price = self.params.get("max_price_ton")
        if max_price is not None and price > float(max_price):
            return BuyDecision(False, "price > max_price_ton")

        min_score = self.params.get("min_rarity_score")
        if min_score is not None and analysis.rarity_score < float(min_score):
            return BuyDecision(False, f"score {analysis.rarity_score} < min")

        max_model = self.params.get("max_model_pct")
        if max_model is not None and float(gift.get("modelRarity") or 100.0) > float(max_model):
            return BuyDecision(False, "model pct > max")

        min_ratio = self.params.get("min_value_ratio")
        if min_ratio is not None and analysis.fair_value > 0:
            if (analysis.fair_value / price) < float(min_ratio):
                return BuyDecision(False, "value ratio < min")

        buy_mult = self.params.get("buy_multiplier")
        if buy_mult is not None and analysis.floor > 0:
            if price > analysis.floor * float(buy_mult):
                return BuyDecision(False, "price > floor*buy_multiplier")

        max_number = self.params.get("max_number")
        if max_number is not None and gift.get("number") is not None:
            if int(gift["number"]) > int(max_number):
                return BuyDecision(False, "number > max_number")

        sell_mult = float(self.params.get("sell_multiplier") or 1.20)
        floor = analysis.floor or analysis.real_floor or price
        sell_at = max(price * sell_mult, floor * sell_mult)
        commission = price * float(user_state.get("commission", 0.05))
        net = sell_at - price - commission
        min_profit = float(self.params.get("min_profit_ton") or 0.0)
        if net < min_profit:
            return BuyDecision(False, "net < min_profit")

        return BuyDecision(
            True,
            "ok",
            expected_profit=round(net, 4),
            sell_price=round(sell_at, 2),
            rarity_score=analysis.rarity_score,
        )
