"""Tests for the advanced market analytics helpers."""

from __future__ import annotations

from analytics.advanced_analytics import (
    cold_collections,
    collection_scorecards,
    floor_z_score,
    hot_collections,
    trending_models,
    volume_profile,
)
from core.market_state import CollectionSnapshot


def _snap(name: str, floor: float, prev: float, volume: int = 0) -> CollectionSnapshot:
    return CollectionSnapshot(
        name=name,
        title=name,
        floor_price=floor,
        previous_floor=prev,
        volume=volume,
    )


def test_hot_collections_ranks_by_growth() -> None:
    snaps = [
        _snap("A", 1.10, 1.00),  # +10%
        _snap("B", 1.20, 1.00),  # +20%
        _snap("C", 1.02, 1.00),  # +2% (under threshold)
        _snap("D", 0.90, 1.00),  # -10%
    ]
    rows = hot_collections(snaps, threshold_pct=5.0)
    assert [r.name for r in rows] == ["B", "A"]
    assert rows[0].delta_pct >= 19.99


def test_cold_collections_ranks_by_drop() -> None:
    snaps = [
        _snap("A", 0.90, 1.00),  # -10%
        _snap("B", 0.80, 1.00),  # -20%
        _snap("C", 0.99, 1.00),  # -1%
    ]
    rows = cold_collections(snaps, threshold_pct=-5.0)
    assert [r.name for r in rows] == ["B", "A"]


def test_volume_profile_buckets_sum_to_full() -> None:
    listings = [{"price": p} for p in [1.0, 1.2, 1.5, 1.8, 2.0, 2.2, 2.5, 3.0]]
    buckets = volume_profile(listings, bins=4)
    assert len(buckets) == 4
    assert sum(b.count for b in buckets) == len(listings)
    assert sum(b.share_pct for b in buckets) == 100.0


def test_volume_profile_handles_single_price() -> None:
    listings = [{"price": 2.0}, {"price": 2.0}]
    buckets = volume_profile(listings, bins=5)
    assert len(buckets) == 1
    assert buckets[0].count == 2


def test_volume_profile_empty_returns_no_buckets() -> None:
    assert volume_profile([], bins=4) == []


def test_floor_z_score_is_none_for_short_history() -> None:
    assert floor_z_score([1.0, 1.1]) is None


def test_floor_z_score_detects_outlier() -> None:
    history = [1.0, 1.0, 1.0, 1.0, 0.5]  # last is below the mean
    z = floor_z_score(history)
    assert z is not None
    assert z < -1


def test_trending_models_orders_by_count() -> None:
    listings = (
        [{"model": "A", "price": 1.0}] * 5
        + [{"model": "B", "price": 2.0}] * 8
        + [{"model": "C", "price": 0.5}] * 1
    )
    rows = trending_models(listings, min_count=2)
    assert rows[0][0] == "B"
    assert rows[0][1] == 8
    assert rows[1][0] == "A"
    assert all(r[0] != "C" for r in rows)


def test_collection_scorecards_grades() -> None:
    snaps = [
        _snap("A", 1.0, 1.0, volume=500),
    ]
    listings_by = {
        "A": [{"price": p} for p in [1.0, 1.01, 1.02, 1.03, 1.05, 1.06, 1.20, 1.50]],
    }
    cards = collection_scorecards(snaps, listings_by_collection=listings_by)
    assert len(cards) == 1
    assert cards[0].grade in {"S", "A", "B", "C", "D"}
    assert cards[0].cluster_size >= 5  # tight cluster around floor


def test_collection_scorecards_thin_market_warns() -> None:
    snaps = [_snap("Thin", 1.0, 1.0)]
    listings_by = {"Thin": [{"price": 1.0}, {"price": 2.0}]}
    cards = collection_scorecards(snaps, listings_by_collection=listings_by)
    assert any("Тонкий рынок" in n for n in cards[0].notes)
