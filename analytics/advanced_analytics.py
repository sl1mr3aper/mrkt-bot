"""Advanced market analytics: hot/cold collections, momentum, volume profile.

These helpers operate on lists of ``CollectionSnapshot`` objects emitted by
``MarketState`` and on raw listing dicts. All functions are pure / stateless,
so they can be called from handlers without holding locks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median, pstdev
from typing import Any

from .liquidity import LiquidityAnalyzer, LiquidityReport


@dataclass
class HotCollection:
    name: str
    title: str
    floor: float
    previous_floor: float
    delta_pct: float
    volume: float


@dataclass
class VolumeBucket:
    """Single price bucket in a volume profile histogram."""
    low: float
    high: float
    count: int
    share_pct: float


@dataclass
class CollectionScoreCard:
    """Aggregate metrics + verbal grade for a single collection."""
    name: str
    title: str
    listings: int
    floor: float | None
    median_price: float | None
    real_floor: float | None
    spread_pct: float | None
    cluster_size: int
    liquidity: float
    grade: str  # S / A / B / C / D
    notes: list[str] = field(default_factory=list)


def hot_collections(
    snapshots: list[Any],
    *,
    threshold_pct: float = 5.0,
    limit: int = 10,
) -> list[HotCollection]:
    """Return collections whose floor moved up by ≥ ``threshold_pct``."""
    out: list[HotCollection] = []
    for snap in snapshots:
        floor = float(getattr(snap, "floor_price", 0.0) or 0.0)
        prev = float(getattr(snap, "previous_floor", floor) or floor)
        if prev <= 0:
            continue
        delta = (floor - prev) / prev * 100.0
        if delta >= threshold_pct:
            out.append(
                HotCollection(
                    name=getattr(snap, "name", "?"),
                    title=getattr(snap, "title", getattr(snap, "name", "?")),
                    floor=floor,
                    previous_floor=prev,
                    delta_pct=round(delta, 2),
                    volume=float(getattr(snap, "volume", 0.0) or 0.0),
                )
            )
    out.sort(key=lambda c: c.delta_pct, reverse=True)
    return out[:limit]


def cold_collections(
    snapshots: list[Any],
    *,
    threshold_pct: float = -5.0,
    limit: int = 10,
) -> list[HotCollection]:
    """Return collections whose floor moved down by ≥ |threshold_pct|."""
    out: list[HotCollection] = []
    for snap in snapshots:
        floor = float(getattr(snap, "floor_price", 0.0) or 0.0)
        prev = float(getattr(snap, "previous_floor", floor) or floor)
        if prev <= 0:
            continue
        delta = (floor - prev) / prev * 100.0
        if delta <= threshold_pct:
            out.append(
                HotCollection(
                    name=getattr(snap, "name", "?"),
                    title=getattr(snap, "title", getattr(snap, "name", "?")),
                    floor=floor,
                    previous_floor=prev,
                    delta_pct=round(delta, 2),
                    volume=float(getattr(snap, "volume", 0.0) or 0.0),
                )
            )
    out.sort(key=lambda c: c.delta_pct)
    return out[:limit]


def volume_profile(
    listings: list[dict[str, Any]],
    *,
    bins: int = 10,
) -> list[VolumeBucket]:
    """Build a price histogram of listings (typically one collection)."""
    prices = [float(x.get("price") or 0.0) for x in listings if x.get("price")]
    prices = [p for p in prices if p > 0]
    if not prices or bins <= 0:
        return []
    lo, hi = min(prices), max(prices)
    if hi == lo:
        return [VolumeBucket(low=lo, high=hi, count=len(prices), share_pct=100.0)]
    step = (hi - lo) / bins
    buckets: list[VolumeBucket] = []
    for i in range(bins):
        bl = lo + step * i
        bh = bl + step
        if i == bins - 1:
            bh = hi + 1e-9
        cnt = sum(1 for p in prices if bl <= p < bh)
        buckets.append(
            VolumeBucket(
                low=round(bl, 4),
                high=round(bh, 4),
                count=cnt,
                share_pct=round(cnt * 100.0 / len(prices), 2),
            )
        )
    return buckets


def collection_scorecards(
    snapshots: list[Any],
    *,
    listings_by_collection: dict[str, list[dict[str, Any]]],
    limit: int = 25,
) -> list[CollectionScoreCard]:
    """Score and rank collections by combined depth/spread/volume metrics."""
    cards: list[CollectionScoreCard] = []
    for snap in snapshots:
        name = getattr(snap, "name", "?")
        title = getattr(snap, "title", name)
        listings = listings_by_collection.get(name, [])
        report = LiquidityAnalyzer.analyse(listings)
        liq = LiquidityAnalyzer.liquidity_factor(
            report, sales_24h=int(getattr(snap, "volume", 0.0) or 0.0)
        )
        notes: list[str] = []
        if (report.spread_pct or 0) < 1.0:
            notes.append("Узкий спред у floor — стабильный рынок.")
        if report.cluster_size_at_floor >= 5:
            notes.append("Глубокий кластер у floor — хорошо для скальпинга.")
        if report.listings_count < 8:
            notes.append("Тонкий рынок — высокий риск slippage.")
        grade = _score_to_grade(_combined_score(report, liq))
        cards.append(
            CollectionScoreCard(
                name=name,
                title=title,
                listings=report.listings_count,
                floor=report.floor,
                median_price=report.median_price,
                real_floor=report.real_floor,
                spread_pct=report.spread_pct,
                cluster_size=report.cluster_size_at_floor,
                liquidity=liq,
                grade=grade,
                notes=notes,
            )
        )
    cards.sort(key=lambda c: c.liquidity, reverse=True)
    return cards[:limit]


def _combined_score(report: LiquidityReport, liq_factor: float) -> float:
    """Combine spread / cluster / liquidity into a single 0..1 score."""
    spread = report.spread_pct if report.spread_pct is not None else 100.0
    spread_score = max(0.0, 1.0 - spread / 20.0)
    cluster_score = min(1.0, report.cluster_size_at_floor / 8.0)
    return 0.35 * spread_score + 0.25 * cluster_score + 0.40 * liq_factor


def _score_to_grade(score: float) -> str:
    if score >= 0.85:
        return "S"
    if score >= 0.70:
        return "A"
    if score >= 0.55:
        return "B"
    if score >= 0.40:
        return "C"
    return "D"


def trending_models(
    listings: list[dict[str, Any]],
    *,
    min_count: int = 3,
    limit: int = 10,
) -> list[tuple[str, int, float]]:
    """Return ``(model, count, median_price)`` for top models by listing count."""
    by_model: dict[str, list[float]] = {}
    for it in listings:
        m = it.get("model")
        p = float(it.get("price") or 0.0)
        if not m or p <= 0:
            continue
        by_model.setdefault(m, []).append(p)
    rows = [
        (m, len(prices), round(median(prices), 3))
        for m, prices in by_model.items()
        if len(prices) >= min_count
    ]
    rows.sort(key=lambda r: r[1], reverse=True)
    return rows[:limit]


def floor_z_score(history: list[float]) -> float | None:
    """Return how many σ the most recent point is from the mean. ``None`` if
    history is too short or has zero variance."""
    if len(history) < 4:
        return None
    m = mean(history)
    sd = pstdev(history)
    if sd == 0:
        return None
    return round((history[-1] - m) / sd, 3)
