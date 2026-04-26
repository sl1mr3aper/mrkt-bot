"""NumberHunter — collect low-numbered NFTs (#1–#999)."""

from __future__ import annotations

from typing import Any

from .base import BaseStrategy, BuyDecision


class NumberHunterStrategy(BaseStrategy):
    type_id = "NumberHunter"
    display_name = "NumberHunter"
    description = "Собирает низкие номера #1–#999."
    default_params = {
        "max_number": 999,
        "max_buy_multiplier": 3.0,
        "min_profit_ton": 0.10,
        "premium_table": {
            "1": 500.0,
            "10": 200.0,
            "100": 100.0,
            "500": 50.0,
            "999": 20.0,
        },
    }

    def _premium(self, number: int) -> float:
        table = {int(k): float(v) for k, v in self.params.get("premium_table", {}).items()}
        for threshold in sorted(table):
            if number <= threshold:
                return table[threshold] / 100.0
        return 0.20

    def should_buy(
        self,
        *,
        gift: dict[str, Any],
        analysis: Any,
        user_state: dict[str, Any],
    ) -> BuyDecision:
        number = gift.get("number")
        if number is None or int(number) > int(self.params["max_number"]):
            return BuyDecision(False, "Слишком высокий номер")

        price = float(gift.get("price") or 0.0)
        floor = analysis.floor or analysis.real_floor or 0.0
        if floor <= 0:
            return BuyDecision(False, "no floor")
        max_buy = floor * float(self.params["max_buy_multiplier"])
        if price > max_buy:
            return BuyDecision(False, f"price {price} > {max_buy:.2f} (floor*{self.params['max_buy_multiplier']})")

        premium = self._premium(int(number))
        fair = max(analysis.fair_value, floor * (1 + premium))
        sell_at = fair * 0.85
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
            extras={"number_premium": premium},
        )
