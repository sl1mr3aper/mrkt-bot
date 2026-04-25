"""PriceAnalyzer tests."""

from __future__ import annotations

import pytest

from core.price_analyzer import PriceAnalyzer


def test_calculate_sell_price_respects_break_even() -> None:
    pa = PriceAnalyzer(commission=0.05)
    sell = pa.calculate_sell_price(
        buy_price=10.0,
        floor_price=10.0,
        fair_value=10.0,
        rarity_score=3.0,
    )
    # min_sell = 10 * 1.10 = 11
    assert sell >= 11.0


def test_calculate_sell_price_legendary_uses_fair_value() -> None:
    pa = PriceAnalyzer(commission=0.05)
    sell = pa.calculate_sell_price(
        buy_price=5.0,
        floor_price=5.0,
        fair_value=40.0,  # 8x floor → legendary band
        rarity_score=9.6,
    )
    # max(min_sell=5.5, fair*0.85=34, floor*1.15=5.75, fair*0.70=28) → 34
    assert sell == pytest.approx(34.0, rel=0.01)


def test_analyse_uses_real_floor() -> None:
    pa = PriceAnalyzer(commission=0.05)
    listings = [{"price": 1.0}, {"price": 1.05}, {"price": 1.10}]
    gift = {"id": "g", "price": 0.95, "modelRarity": 5.0, "backdropRarity": 5.0, "symbolRarity": 5.0}
    a = pa.analyse(gift, listings, floor=1.0)
    assert a.is_below_real_floor
    assert a.fair_value > 0
