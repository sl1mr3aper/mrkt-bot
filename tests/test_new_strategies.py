"""Tests for the Arbitrage / MeanReversion / ScalperPro strategies."""

from __future__ import annotations

from dataclasses import dataclass

from strategies import ArbitrageStrategy, MeanReversionStrategy, ScalperProStrategy


@dataclass
class _Analysis:
    floor: float = 1.0
    rarity_score: float = 5.0
    cluster_size_at_floor: int = 0
    spread_pct: float = 0.0
    fair_value: float = 1.5


# ─── Arbitrage ─────────────────────────────────────────────────────


def test_arbitrage_buys_when_spread_is_wide() -> None:
    strat = ArbitrageStrategy({"min_spread_pct": 20.0, "max_position_ton": 5.0})
    gift = {"price": 1.0, "collection": "A", "model": "M"}
    listings = [
        {"price": 2.0, "collection": "A", "model": "M"},
        {"price": 2.5, "collection": "A", "model": "M"},
        {"price": 3.0, "collection": "A", "model": "M"},
    ]
    decision = strat.should_buy(
        gift=gift,
        analysis=_Analysis(),
        user_state={"market_listings": listings, "commission": 0.05},
    )
    assert decision.should_buy is True
    assert decision.expected_profit and decision.expected_profit > 0


def test_arbitrage_skips_when_spread_too_small() -> None:
    strat = ArbitrageStrategy({"min_spread_pct": 25.0})
    gift = {"price": 1.0, "collection": "A", "model": "M"}
    listings = [{"price": 1.05, "collection": "A", "model": "M"}] * 3
    decision = strat.should_buy(
        gift=gift,
        analysis=_Analysis(),
        user_state={"market_listings": listings, "commission": 0.05},
    )
    assert decision.should_buy is False


def test_arbitrage_skips_when_no_peers() -> None:
    strat = ArbitrageStrategy()
    decision = strat.should_buy(
        gift={"price": 1.0, "collection": "Z", "model": "M"},
        analysis=_Analysis(),
        user_state={"market_listings": [], "commission": 0.05},
    )
    assert decision.should_buy is False


# ─── MeanReversion ─────────────────────────────────────────────────


def test_mean_reversion_buys_below_threshold() -> None:
    strat = MeanReversionStrategy({"k_std": 1.0, "min_profit_ton": 0.0})
    decision = strat.should_buy(
        gift={"price": 0.5, "floor_price": 0.5},
        analysis=_Analysis(floor=0.5),
        user_state={
            "floor_history": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.5],
            "commission": 0.05,
        },
    )
    assert decision.should_buy is True


def test_mean_reversion_skips_when_floor_above_mean() -> None:
    strat = MeanReversionStrategy()
    decision = strat.should_buy(
        gift={"price": 1.0},
        analysis=_Analysis(floor=1.0),
        user_state={
            "floor_history": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            "commission": 0.05,
        },
    )
    assert decision.should_buy is False


def test_mean_reversion_short_history_skips() -> None:
    strat = MeanReversionStrategy()
    decision = strat.should_buy(
        gift={"price": 1.0},
        analysis=_Analysis(),
        user_state={"floor_history": [1.0], "commission": 0.05},
    )
    assert decision.should_buy is False


# ─── ScalperPro ────────────────────────────────────────────────────


def test_scalper_pro_buys_with_deep_cluster() -> None:
    strat = ScalperProStrategy({"min_profit_ton": 0.0})
    decision = strat.should_buy(
        gift={"price": 1.0},
        analysis=_Analysis(floor=1.0, cluster_size_at_floor=8, spread_pct=4.0),
        user_state={"commission": 0.01},
    )
    assert decision.should_buy is True


def test_scalper_pro_skips_when_above_floor() -> None:
    strat = ScalperProStrategy()
    decision = strat.should_buy(
        gift={"price": 1.10},
        analysis=_Analysis(floor=1.00, cluster_size_at_floor=10, spread_pct=5.0),
        user_state={"commission": 0.05},
    )
    assert decision.should_buy is False


def test_scalper_pro_skips_with_thin_cluster() -> None:
    strat = ScalperProStrategy()
    decision = strat.should_buy(
        gift={"price": 1.0},
        analysis=_Analysis(floor=1.0, cluster_size_at_floor=1, spread_pct=10.0),
        user_state={"commission": 0.05},
    )
    assert decision.should_buy is False


def test_scalper_pro_skips_with_narrow_spread() -> None:
    strat = ScalperProStrategy({"micro_spread_pct": 5.0})
    decision = strat.should_buy(
        gift={"price": 1.0},
        analysis=_Analysis(floor=1.0, cluster_size_at_floor=8, spread_pct=1.0),
        user_state={"commission": 0.05},
    )
    assert decision.should_buy is False
