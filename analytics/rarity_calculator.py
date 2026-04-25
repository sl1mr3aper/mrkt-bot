"""Universal rarity scoring + fair value estimation.

Works with raw gift dicts coming back from the MRKT API or `amrkt.Gift`.
No collection-specific hard-coding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FairValue:
    base: float
    adjusted: float
    multiplier: float
    rarity_score: float
    liquidity_factor: float
    number_premium: float


class RarityCalculator:
    """Convert per-trait rarity percentages into a single 0..10 score."""

    # Weights — Model dominates pricing, then Backdrop, then Symbol.
    WEIGHT_MODEL = 0.55
    WEIGHT_BACKDROP = 0.30
    WEIGHT_SYMBOL = 0.15

    # Multiplier table for fair value.
    MULTIPLIER_TABLE: list[tuple[float, float, float]] = [
        # (low, high, multiplier)
        (9.5, 10.01, 8.0),  # Legendary
        (8.5, 9.5, 5.0),    # Epic
        (7.0, 8.5, 3.0),    # Rare
        (5.5, 7.0, 1.8),    # Uncommon
        (4.0, 5.5, 1.3),    # Common+
        (0.0, 4.0, 1.0),    # Common
    ]

    # ─── Score ──────────────────────────────────────────────

    def calculate_score(self, gift: dict[str, Any]) -> float:
        """Return rarity score in [0, 10]."""
        model_pct = self._extract_pct(gift, "model")
        backdrop_pct = self._extract_pct(gift, "backdrop")
        symbol_pct = self._extract_pct(gift, "symbol")

        score = (
            self._pct_to_score(model_pct) * self.WEIGHT_MODEL
            + self._pct_to_score(backdrop_pct) * self.WEIGHT_BACKDROP
            + self._pct_to_score(symbol_pct) * self.WEIGHT_SYMBOL
        )

        score += self.number_bonus(gift.get("number"))
        if gift.get("mintable") or gift.get("minted"):
            score += 0.2

        return round(min(score, 10.0), 2)

    @staticmethod
    def _extract_pct(gift: dict[str, Any], kind: str) -> float:
        """Read percentage value from the gift dict, robust to several shapes."""
        keys = (
            f"{kind}Rarity",
            f"{kind}_rarity",
            f"{kind}_rarity_percent",
            f"{kind}RarityPercent",
            f"{kind}RarityPerMille",
            f"{kind}_rarity_per_mille",
        )
        for key in keys:
            if key in gift and gift[key] is not None:
                value = float(gift[key])
                if "PerMille" in key or "per_mille" in key:
                    return value / 10.0
                return value
        return 50.0

    @staticmethod
    def _pct_to_score(pct: float) -> float:
        """Convert occurrence-percent → 0..10 sub-score (lower pct = higher score)."""
        p = pct / 100.0  # 5% → 0.05
        if p <= 0.001:
            return 10.0
        if p <= 0.005:
            return 9.5
        if p <= 0.01:
            return 9.0
        if p <= 0.02:
            return 8.0
        if p <= 0.05:
            return 7.0
        if p <= 0.10:
            return 5.5
        if p <= 0.20:
            return 4.0
        if p <= 0.40:
            return 2.5
        return 1.0

    @staticmethod
    def number_bonus(number: int | None) -> float:
        """Bonus for low NFT numbers (#1-#999)."""
        if number is None:
            return 0.0
        if number <= 10:
            return 1.5
        if number <= 50:
            return 1.0
        if number <= 100:
            return 0.7
        if number <= 500:
            return 0.4
        if number <= 999:
            return 0.2
        return 0.0

    # ─── Fair value ─────────────────────────────────────────

    def estimate_fair_value(
        self,
        gift: dict[str, Any],
        floor_price: float,
        *,
        liquidity_factor: float = 1.0,
    ) -> float:
        """Estimate fair market price; reduces by liquidity factor."""
        score = self.calculate_score(gift)
        multiplier = self._multiplier_for_score(score)
        base = floor_price * multiplier
        adjusted = base * max(0.4, min(1.0, liquidity_factor))
        return round(adjusted, 2)

    def fair_value_breakdown(
        self,
        gift: dict[str, Any],
        floor_price: float,
        *,
        liquidity_factor: float = 1.0,
    ) -> FairValue:
        score = self.calculate_score(gift)
        multiplier = self._multiplier_for_score(score)
        base = floor_price * multiplier
        liq = max(0.4, min(1.0, liquidity_factor))
        return FairValue(
            base=round(base, 2),
            adjusted=round(base * liq, 2),
            multiplier=multiplier,
            rarity_score=score,
            liquidity_factor=liq,
            number_premium=self.number_bonus(gift.get("number")),
        )

    def _multiplier_for_score(self, score: float) -> float:
        for low, high, mult in self.MULTIPLIER_TABLE:
            if low <= score < high:
                return mult
        return 1.0
