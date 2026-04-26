"""Price / fair-value analysis combining rarity + liquidity + sales velocity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from analytics.liquidity import LiquidityAnalyzer, LiquidityReport
from analytics.rarity_calculator import FairValue, RarityCalculator


@dataclass
class TradeAnalysis:
    gift: dict[str, Any]
    floor: float
    fair_value: float
    rarity_score: float
    multiplier: float
    liquidity: LiquidityReport
    liquidity_factor: float
    expected_profit: float
    expected_profit_pct: float
    real_floor: float
    is_below_real_floor: bool


class PriceAnalyzer:
    """High-level analysis used by strategies & engine."""

    def __init__(
        self,
        commission: float = 0.05,
        rarity: RarityCalculator | None = None,
    ) -> None:
        self.commission = commission
        self.rarity = rarity or RarityCalculator()

    # ─── basic helpers ─────────────────────────────────────

    def calculate_score(self, gift: dict[str, Any]) -> float:
        return self.rarity.calculate_score(gift)

    def fair_value_breakdown(
        self, gift: dict[str, Any], floor: float, *, liquidity_factor: float = 1.0
    ) -> FairValue:
        return self.rarity.fair_value_breakdown(
            gift, floor, liquidity_factor=liquidity_factor
        )

    # ─── main entry ─────────────────────────────────────────

    def analyse(
        self,
        gift: dict[str, Any],
        listings: list[Any],
        *,
        floor: float | None = None,
        sales_24h: int = 0,
    ) -> TradeAnalysis:
        report = LiquidityAnalyzer.analyse(listings)
        liq_factor = LiquidityAnalyzer.liquidity_factor(report, sales_24h=sales_24h)

        true_floor = floor or report.real_floor or report.floor or 0.0
        breakdown = self.fair_value_breakdown(
            gift, true_floor, liquidity_factor=liq_factor
        )

        price = float(gift.get("price") or 0.0)
        expected_profit = breakdown.adjusted - price - price * self.commission
        expected_profit_pct = (
            (expected_profit / price) * 100.0 if price > 0 else 0.0
        )

        real_floor = report.real_floor or report.floor or true_floor
        return TradeAnalysis(
            gift=gift,
            floor=true_floor,
            fair_value=breakdown.adjusted,
            rarity_score=breakdown.rarity_score,
            multiplier=breakdown.multiplier,
            liquidity=report,
            liquidity_factor=liq_factor,
            expected_profit=round(expected_profit, 4),
            expected_profit_pct=round(expected_profit_pct, 2),
            real_floor=round(real_floor, 2),
            is_below_real_floor=price > 0 and price < real_floor,
        )

    # ─── sell price calculation ────────────────────────────

    def calculate_sell_price(
        self,
        *,
        buy_price: float,
        floor_price: float,
        fair_value: float,
        rarity_score: float,
        sell_multiplier: float = 1.15,
    ) -> float:
        """Algorithm 4.3 (sell price)."""
        min_sell = buy_price * (1 + self.commission * 2)
        targets: list[float] = [
            min_sell,
            fair_value * 0.85,
            floor_price * sell_multiplier,
        ]
        target = max(targets)
        if rarity_score > 7:
            target = max(target, fair_value * 0.70)
        return round(target, 2)
