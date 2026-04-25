"""Tests for ``PortfolioAnalyzer``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from analytics.portfolio_analyzer import PortfolioAnalyzer


@dataclass
class _Item:
    id: int
    gift_name: str
    collection: str
    buy_price: float
    bought_at: datetime


def _now(minutes: int = 0) -> datetime:
    return datetime.now(UTC) - timedelta(minutes=minutes)


def test_aggregates_total_and_pnl() -> None:
    items = [
        _Item(1, "Gift A", "ColA", 1.0, _now(60)),
        _Item(2, "Gift B", "ColA", 2.0, _now(30)),
        _Item(3, "Gift C", "ColB", 0.5, _now(120)),
    ]
    floors = {"ColA": 1.5, "ColB": 0.6}
    rpt = PortfolioAnalyzer.analyse(items, floors=floors)
    # Bought 1 + 2 + 0.5 = 3.5, now 1.5 + 1.5 + 0.6 = 3.6, +0.10
    assert rpt.total_invested == 3.5
    assert rpt.total_value_now == 3.6
    assert rpt.unrealised_pnl == 0.1
    assert rpt.unrealised_pct == round(0.1 / 3.5 * 100.0, 2)


def test_reports_biggest_winner_and_loser() -> None:
    items = [
        _Item(1, "Win", "A", 1.0, _now(10)),
        _Item(2, "Lose", "A", 1.0, _now(10)),
    ]
    floors = {"A": 1.0}  # one floor for all — but per-position both are equal
    rpt = PortfolioAnalyzer.analyse(items, floors=floors)
    assert rpt.biggest_winner is not None
    assert rpt.biggest_loser is not None


def test_exposure_by_collection() -> None:
    items = [
        _Item(1, "A1", "Alpha", 1.0, _now(1)),
        _Item(2, "A2", "Alpha", 2.5, _now(1)),
        _Item(3, "B1", "Beta", 0.7, _now(1)),
    ]
    rpt = PortfolioAnalyzer.analyse(items, floors={})
    assert rpt.by_collection["Alpha"] == 3.5
    assert rpt.by_collection["Beta"] == 0.7


def test_empty_portfolio_returns_zeroes() -> None:
    rpt = PortfolioAnalyzer.analyse([], floors={})
    assert rpt.total_invested == 0
    assert rpt.unrealised_pnl == 0
    assert rpt.biggest_winner is None
    assert rpt.biggest_loser is None
    assert rpt.by_collection == {}


def test_render_includes_summary_lines() -> None:
    items = [
        _Item(1, "A1", "Alpha", 1.0, _now(60)),
        _Item(2, "B1", "Beta", 0.5, _now(60)),
    ]
    rpt = PortfolioAnalyzer.analyse(items, floors={"Alpha": 1.5, "Beta": 0.4})
    text = PortfolioAnalyzer.render(rpt)
    assert "Portfolio Analytics" in text
    assert "Инвестировано" in text
    assert "Экспозиция" in text
    assert "Alpha" in text
