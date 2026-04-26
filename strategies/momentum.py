"""Momentum — hype trading with tight trailing stop."""

from __future__ import annotations

from typing import Any

from .base import BaseStrategy, BuyDecision


class MomentumStrategy(BaseStrategy):
    type_id = "Momentum"
    display_name = "Momentum"
    description = "Лови хайп — выходи быстро."
    default_params = {
        "volume_spike_pct": 50.0,
        "buy_window_minutes": 30,
        "sell_target_pct": 30.0,
        "hard_stop_pct": -10.0,
        "max_hold_hours": 4,
        "max_buy_ton": 5.0,
        "min_profit_ton": 0.20,
    }

    def should_buy(
        self,
        *,
        gift: dict[str, Any],
        analysis: Any,
        user_state: dict[str, Any],
    ) -> BuyDecision:
        # Momentum requires recent volume info passed in via analysis.extras.
        # When we don't have it, conservatively decline.
        spike = float(getattr(analysis, "volume_spike_pct", 0.0) or 0.0)
        if spike < float(self.params["volume_spike_pct"]):
            return BuyDecision(False, f"volume spike {spike:.1f}% мал")

        price = float(gift.get("price") or 0.0)
        if price > float(self.params["max_buy_ton"]):
            return BuyDecision(False, "price > max_buy_ton")
        if price <= 0:
            return BuyDecision(False, "no price")

        sell_at = price * (1 + float(self.params["sell_target_pct"]) / 100.0)
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
            extras={"momentum_spike": spike},
        )
