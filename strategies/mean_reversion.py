"""Mean-reversion strategy — buy when floor deviates below 7-day mean."""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any

from .base import BaseStrategy, BuyDecision


class MeanReversionStrategy(BaseStrategy):
    """Buys when current floor < mean(7d) − k_std × std(7d)."""

    type_id = "MeanReversion"
    display_name = "MeanReversion"
    description = "Возврат к 7-дневной средней. Buy при отклонении вниз ≥ 1σ."
    default_params = {
        "window_days": 7,
        "k_std": 1.0,
        "sell_multiplier": 1.10,
        "min_profit_ton": 0.3,
        "max_position_ton": 15.0,
        "max_positions": 4,
    }

    def should_buy(
        self,
        *,
        gift: dict[str, Any],
        analysis: Any,
        user_state: dict[str, Any],
    ) -> BuyDecision:
        price = float(gift.get("price") or 0.0)
        floor = float(getattr(analysis, "floor", 0.0) or 0.0)
        if price <= 0 or floor <= 0:
            return BuyDecision(False, "Нет данных")
        if price > float(self.params["max_position_ton"]):
            return BuyDecision(False, "Цена > max_position_ton")

        # The history is provided by the engine via user_state["floor_history"].
        history = [float(x) for x in (user_state.get("floor_history") or []) if x is not None]
        if len(history) < 6:
            return BuyDecision(False, "Недостаточно истории")
        m = mean(history)
        sd = pstdev(history) if len(history) >= 2 else 0.0
        if sd == 0:
            return BuyDecision(False, "Нулевое стд. отклонение")

        threshold = m - float(self.params["k_std"]) * sd
        if floor > threshold:
            return BuyDecision(
                False,
                f"floor {floor:.3f} > mean−kσ ({threshold:.3f})",
            )

        # Best-case: floor reverts to mean.
        target = m * float(self.params["sell_multiplier"])
        commission = price * float(user_state.get("commission", 0.05))
        net = target - price - commission
        if net < float(self.params["min_profit_ton"]):
            return BuyDecision(False, f"profit {net:.3f} < min")
        return BuyDecision(
            True,
            f"mean-reversion z={(floor - m) / sd:.2f}",
            expected_profit=round(net, 4),
            sell_price=round(target, 2),
            rarity_score=getattr(analysis, "rarity_score", 0.0) or 0.0,
            extras={"mean": round(m, 4), "std": round(sd, 4), "z": round((floor - m) / sd, 3)},
        )
