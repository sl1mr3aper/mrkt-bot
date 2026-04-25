"""Liquidity / order-book depth analytics."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, median
from typing import Any


@dataclass
class LiquidityReport:
    listings_count: int
    floor: float | None
    real_floor: float | None  # weighted avg of cheapest N
    median_price: float | None
    spread_pct: float | None  # 2nd lowest vs floor
    cluster_size_at_floor: int  # how many listings within +5% of floor
    listings_at_or_below_floor: int


class LiquidityAnalyzer:
    """Computes liquidity metrics on a list of gift listings.

    Each listing dict must expose at least ``sale_price_ton`` (or ``salePrice``
    in nanoTON which is auto-converted).
    """

    @staticmethod
    def _price_ton(item: Any) -> float | None:
        if isinstance(item, dict):
            for key in ("sale_price_ton", "salePriceTon", "price_ton", "price"):
                if key in item and item[key] is not None:
                    return float(item[key])
            for key in ("salePrice", "sale_price"):
                if key in item and item[key] is not None:
                    return float(item[key]) / 1_000_000_000
            return None
        # amrkt.Gift duck-typing
        for attr in ("sale_price_ton", "price_ton"):
            if hasattr(item, attr):
                value = getattr(item, attr)
                if value is not None:
                    return float(value)
        return None

    @classmethod
    def analyse(cls, listings: list[Any], top_n: int = 5) -> LiquidityReport:
        prices = [p for p in (cls._price_ton(x) for x in listings) if p is not None]
        prices.sort()

        if not prices:
            return LiquidityReport(0, None, None, None, None, 0, 0)

        floor = prices[0]
        cheapest = prices[: min(top_n, len(prices))]
        real_floor = round(mean(cheapest), 2)
        med = round(median(prices), 2)

        spread_pct: float | None = None
        if len(prices) >= 2:
            spread_pct = round((prices[1] - floor) / floor * 100.0, 2)

        cluster_threshold = floor * 1.05
        cluster = sum(1 for p in prices if p <= cluster_threshold)
        below_floor = sum(1 for p in prices if p <= floor)

        return LiquidityReport(
            listings_count=len(prices),
            floor=floor,
            real_floor=real_floor,
            median_price=med,
            spread_pct=spread_pct,
            cluster_size_at_floor=cluster,
            listings_at_or_below_floor=below_floor,
        )

    @staticmethod
    def liquidity_factor(report: LiquidityReport, *, sales_24h: int = 0) -> float:
        """Heuristic 0..1 factor used by the rarity calculator.

        Higher = more liquid → fair value closer to the theoretical multiplier.
        """
        if report.listings_count == 0:
            return 0.5
        velocity = sales_24h / max(1, report.listings_count)
        depth = min(1.0, report.cluster_size_at_floor / 5.0)
        score = 0.4 + 0.4 * min(1.0, velocity) + 0.2 * depth
        return round(min(1.0, max(0.4, score)), 3)
