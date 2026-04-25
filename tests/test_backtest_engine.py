"""Tests for the lightweight backtest engine."""

from __future__ import annotations

from core.backtest_engine import BacktestEngine, BacktestReport
from strategies import FloorMultiplierStrategy, ScalperProStrategy


def _listings_at_floor(n: int, floor: float = 1.0) -> list[dict]:
    return [
        {
            "id": f"g{i}",
            "title": f"Gift #{i}",
            "name": f"Gift #{i}",
            "collection": "X",
            "model": "M",
            "price": floor,
            "floor_price": floor,
            "rarity_score": 100.0,
        }
        for i in range(n)
    ]


def test_floor_multiplier_buys_at_floor_and_records_profit() -> None:
    strategy = FloorMultiplierStrategy(
        {"buy_multiplier": 1.0, "sell_multiplier": 1.20, "min_profit_ton": 0.0}
    )
    engine = BacktestEngine(commission_pct=0.05)
    listings = _listings_at_floor(10, floor=1.0)
    report = engine.run(strategy, listings)
    assert isinstance(report, BacktestReport)
    assert report.candidates_seen == 10
    assert report.trades_count > 0
    assert report.total_profit > 0
    assert 0.0 <= report.win_rate <= 1.0


def test_scalper_pro_with_thin_market_skips_all() -> None:
    strategy = ScalperProStrategy()
    engine = BacktestEngine()
    listings = _listings_at_floor(5)
    for x in listings:
        x["cluster_size_at_floor"] = 0
    report = engine.run(strategy, listings)
    assert report.trades_count == 0
    assert report.skipped_reasons  # something was rejected


def test_render_returns_summary() -> None:
    strategy = FloorMultiplierStrategy()
    engine = BacktestEngine()
    listings = _listings_at_floor(3)
    text = engine.run(strategy, listings).render()
    assert "Стратегия" in text
    assert "Просмотрено листингов" in text
    assert "Win-rate" in text


def test_empty_listings_produce_empty_report() -> None:
    strategy = FloorMultiplierStrategy()
    engine = BacktestEngine()
    report = engine.run(strategy, [])
    assert report.candidates_seen == 0
    assert report.trades_count == 0
    assert report.total_profit == 0
