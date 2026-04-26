"""Strategy unit tests using the in-memory analyzer."""

from __future__ import annotations

from core.price_analyzer import PriceAnalyzer
from strategies import (
    FloorMultiplierStrategy,
    FloorSniperStrategy,
    NumberHunterStrategy,
    RaritySniperStrategy,
    UndervalueHunterStrategy,
)

ANALYZER = PriceAnalyzer(commission=0.05)


def _state() -> dict:
    return {
        "balance_ton": 100,
        "active_positions": 0,
        "daily_buys": 0,
        "daily_loss": 0,
        "min_profit_ton": 0.05,
        "max_buy_ton": 100,
        "max_daily_trades": 50,
        "max_daily_loss_ton": 100,
        "stop_loss_pct": 15,
        "commission": 0.05,
    }


def _gift(price: float, **kwargs):
    return {
        "id": "g1",
        "price": price,
        "modelRarity": kwargs.get("model_pct", 50.0),
        "backdropRarity": kwargs.get("backdrop_pct", 50.0),
        "symbolRarity": kwargs.get("symbol_pct", 50.0),
        "collection": "Test",
        "number": kwargs.get("number"),
    }


def _analysis(gift: dict, floor: float, listings: list | None = None):
    return ANALYZER.analyse(gift, listings or [{"price": floor}], floor=floor)


def test_floor_multiplier_buys_at_floor() -> None:
    s = FloorMultiplierStrategy(analyzer=ANALYZER)
    decision = s.should_buy(
        gift=_gift(1.0), analysis=_analysis(_gift(1.0), floor=1.0), user_state=_state()
    )
    assert decision.should_buy
    assert decision.sell_price > 1.0


def test_floor_multiplier_rejects_above_floor() -> None:
    s = FloorMultiplierStrategy(analyzer=ANALYZER)
    decision = s.should_buy(
        gift=_gift(1.5), analysis=_analysis(_gift(1.5), floor=1.0), user_state=_state()
    )
    assert not decision.should_buy


def test_rarity_sniper_buys_undervalued_rare() -> None:
    s = RaritySniperStrategy(analyzer=ANALYZER)
    rare_gift = _gift(2.0, model_pct=0.5, backdrop_pct=1.0, symbol_pct=2.0)
    decision = s.should_buy(
        gift=rare_gift, analysis=_analysis(rare_gift, floor=2.0), user_state=_state()
    )
    assert decision.should_buy


def test_undervalue_hunter_requires_rare_model() -> None:
    s = UndervalueHunterStrategy(analyzer=ANALYZER)
    common_gift = _gift(1.0, model_pct=20.0)
    assert not s.should_buy(
        gift=common_gift,
        analysis=_analysis(common_gift, floor=1.0),
        user_state=_state(),
    ).should_buy


def test_floor_sniper_below_floor() -> None:
    s = FloorSniperStrategy(analyzer=ANALYZER)
    cheap = _gift(0.85)
    decision = s.should_buy(
        gift=cheap,
        analysis=_analysis(cheap, floor=1.0),
        user_state=_state(),
    )
    assert decision.should_buy


def test_number_hunter_low_numbers() -> None:
    s = NumberHunterStrategy(analyzer=ANALYZER)
    low = _gift(2.0, number=10)
    decision = s.should_buy(
        gift=low, analysis=_analysis(low, floor=1.0), user_state=_state()
    )
    assert decision.should_buy

    high = _gift(2.0, number=2000)
    assert not s.should_buy(
        gift=high, analysis=_analysis(high, floor=1.0), user_state=_state()
    ).should_buy
