"""Strategy registry."""

from __future__ import annotations

from .base import BaseStrategy, BuyDecision
from .custom import CustomStrategy
from .floor_multiplier import FloorMultiplierStrategy
from .floor_sniper import FloorSniperStrategy
from .momentum import MomentumStrategy
from .number_hunter import NumberHunterStrategy
from .rarity_sniper import RaritySniperStrategy
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
        CustomStrategy,
    )
}

__all__ = [
    "STRATEGY_REGISTRY",
    "BaseStrategy",
    "BuyDecision",
    "CustomStrategy",
    "FloorMultiplierStrategy",
    "FloorSniperStrategy",
    "MomentumStrategy",
    "NumberHunterStrategy",
    "RaritySniperStrategy",
    "UndervalueHunterStrategy",
]
