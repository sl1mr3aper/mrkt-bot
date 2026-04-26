"""Arbitrage strategy — exploit intra-collection model price gaps."""

from __future__ import annotations

from statistics import median
from typing import Any

from .base import BaseStrategy, BuyDecision


class ArbitrageStrategy(BaseStrategy):
    """Buys a model whose listing price is significantly below the model's median.

    Useful on tail-end collections where one seller occasionally dumps below
    the model's typical floor and immediately gets re-priced by the market.
    """

    type_id = "Arbitrage"
    display_name = "Arbitrage"
    description = "Сравнение цен между моделями одной коллекции; покупка при ≥25% разнице."
    default_params = {
        "min_spread_pct": 25.0,
        "min_profit_ton": 0.4,
        "max_position_ton": 12.0,
        "max_positions": 3,
        "sell_multiplier": 1.10,
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
            return BuyDecision(False, "Нет цены")
        if price > float(self.params["max_position_ton"]):
            return BuyDecision(False, "Цена > max_position_ton")

        # Within-collection peers
        peers: list[float] = []
        same_model: list[float] = []
        coll = gift.get("collection")
        model = gift.get("model")
        for other in user_state.get("market_listings", []):
            if other.get("collection") != coll:
                continue
            p = float(other.get("price") or 0.0)
            if p > 0:
                peers.append(p)
                if other.get("model") == model:
                    same_model.append(p)

        ref = median(same_model) if same_model else (median(peers) if peers else None)
        if ref is None or ref <= 0:
            return BuyDecision(False, "Недостаточно листингов для анализа")

        spread_pct = (ref - price) / ref * 100.0
        if spread_pct < float(self.params["min_spread_pct"]):
            return BuyDecision(False, f"spread {spread_pct:.1f}% < min")

        target = ref * float(self.params["sell_multiplier"])
        commission = price * float(user_state.get("commission", 0.05))
        net = target - price - commission
        if net < float(self.params["min_profit_ton"]):
            return BuyDecision(False, f"profit {net:.3f} < min")

        return BuyDecision(
            True,
            f"arbitrage spread={spread_pct:.1f}%",
            expected_profit=round(net, 4),
            sell_price=round(target, 2),
            rarity_score=getattr(analysis, "rarity_score", 0.0) or 0.0,
            extras={"reference_price": round(ref, 3), "spread_pct": round(spread_pct, 2)},
        )
