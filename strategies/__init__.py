"""Strategy registry."""

from __future__ import annotations

from .arbitrage import ArbitrageStrategy
from .base import BaseStrategy, BuyDecision
from .custom import CustomStrategy
from .floor_multiplier import FloorMultiplierStrategy
from .floor_sniper import FloorSniperStrategy
from .mean_reversion import MeanReversionStrategy
from .momentum import MomentumStrategy
from .number_hunter import NumberHunterStrategy
from .rarity_sniper import RaritySniperStrategy
from .scalper_pro import ScalperProStrategy
from .undervalue_hunter import UndervalueHunterStrategy

STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    cls.type_id: cls
    for cls in (
        FloorMultiplierStrategy,
        RaritySniperStrategy,
        UndervalueHunterStrategy,
        FloorSniperStrategy,
        MomentumStrategy,
        NumberHunterStrategy,
        ArbitrageStrategy,
        MeanReversionStrategy,
        ScalperProStrategy,
        CustomStrategy,
    )
}

__all__ = [
    "STRATEGY_REGISTRY",
    "ArbitrageStrategy",
    "BaseStrategy",
    "BuyDecision",
    "CustomStrategy",
    "FloorMultiplierStrategy",
    "FloorSniperStrategy",
    "MeanReversionStrategy",
    "MomentumStrategy",
    "NumberHunterStrategy",
    "RaritySniperStrategy",
    "ScalperProStrategy",
    "UndervalueHunterStrategy",
]
