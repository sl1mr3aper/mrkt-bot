"""ScalperPro — high-frequency micro-spread strategy."""

from __future__ import annotations

from typing import Any

from .base import BaseStrategy, BuyDecision


class ScalperProStrategy(BaseStrategy):
    """Very fast in/out trades: only fires on dense-cluster floors with thin spread.

    Targets micro-spreads of 2–5%; relies on high market depth at the floor
    (``cluster_size_at_floor`` reported by ``LiquidityAnalyzer``).
    """

    type_id = "ScalperPro"
    display_name = "ScalperPro"
    description = "Скальпинг 2–5% на ликвидных коллекциях с глубоким стаканом у floor."
    default_params = {
        "micro_spread_pct": 3.0,
        "min_cluster": 5,
        "min_profit_ton": 0.05,
        "max_position_ton": 5.0,
        "max_positions": 8,
        "sell_multiplier": 1.04,
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
        if price > floor * 1.02:
            return BuyDecision(False, "Не на floor")

        cluster = int(getattr(analysis, "cluster_size_at_floor", 0) or 0)
        if cluster < int(self.params["min_cluster"]):
            return BuyDecision(False, f"cluster {cluster} < min")

        # Spread between floor and 2nd-cheapest must be wide enough to flip.
        spread_pct = float(getattr(analysis, "spread_pct", 0.0) or 0.0)
        if spread_pct < float(self.params["micro_spread_pct"]):
            return BuyDecision(False, f"spread {spread_pct:.2f}% < min")

        target = price * float(self.params["sell_multiplier"])
        commission = price * float(user_state.get("commission", 0.05))
        net = target - price - commission
        if net < float(self.params["min_profit_ton"]):
            return BuyDecision(False, f"profit {net:.3f} < min")

        return BuyDecision(
            True,
            f"scalp cluster={cluster} spread={spread_pct:.2f}%",
            expected_profit=round(net, 4),
            sell_price=round(target, 2),
            rarity_score=getattr(analysis, "rarity_score", 0.0) or 0.0,
        )
