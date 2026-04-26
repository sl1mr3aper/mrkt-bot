"""Tests for the synthetic demo dataset used in DRY-RUN mode."""

from __future__ import annotations

import pytest

from core.demo_dataset import (
    BACKDROPS,
    COLLECTIONS,
    SYMBOLS,
    DemoTrade,
    make_collections,
    make_listings,
    make_models_index,
    make_trades,
)


def test_collections_are_realistic() -> None:
    cols = make_collections()
    # User explicitly requested ≥130 collections — assert the canonical
    # catalogue size meets that bar.
    assert len(cols) >= 130
    seen_names = {c["name"] for c in cols}
    assert len(seen_names) == len(cols), "collection names must be unique"
    for c in cols:
        assert c["floor_price"] > 0
        assert c["volume"] >= 0
        assert "title" in c


def test_models_cover_all_collections() -> None:
    idx = make_models_index()
    for c in COLLECTIONS:
        assert c["name"] in idx
        assert len(idx[c["name"]]) >= 3, c["name"]


def test_listings_distribution() -> None:
    listings = make_listings(per_collection=10)
    assert len(listings) == 10 * len(COLLECTIONS)
    for x in listings:
        assert x["price"] > 0
        assert x["collection"] in {c["name"] for c in COLLECTIONS}
        assert x["model"]
        assert x["backdrop"] in BACKDROPS
        assert x["symbol"] in SYMBOLS
        # Rarities are stored as percentages (0..100); composite handled in strategy
        assert 0 <= x["modelRarity"] <= 100
        assert 0 <= x["backdropRarity"] <= 100
        assert 0 <= x["symbolRarity"] <= 100


def test_listings_seed_is_stable() -> None:
    a = make_listings(per_collection=8, seed=1)
    b = make_listings(per_collection=8, seed=1)
    assert [(x["id"], x["price"]) for x in a] == [(x["id"], x["price"]) for x in b]


def test_trades_seed_is_stable() -> None:
    a = make_trades(user_id=1, count=20, seed=99)
    b = make_trades(user_id=1, count=20, seed=99)
    assert all(isinstance(t, DemoTrade) for t in a)
    assert [(t.gift_id, t.net_profit) for t in a] == [
        (t.gift_id, t.net_profit) for t in b
    ]


def test_trades_have_realistic_fields() -> None:
    trades = make_trades(user_id=42, count=30)
    assert len(trades) == 30
    for t in trades:
        assert t.buy_price > 0
        assert t.sell_price > 0
        assert pytest.approx(t.gross_profit, abs=0.01) == round(t.sell_price - t.buy_price, 3)
        assert t.profit_pct == pytest.approx(
            (t.net_profit / t.buy_price) * 100.0 if t.buy_price else 0.0,
            abs=0.5,
        )


def test_trades_span_history_window() -> None:
    """Trades should be spread across the past 30 days."""
    from datetime import UTC, datetime, timedelta

    trades = make_trades(user_id=42, count=50)
    now = datetime.now(UTC)
    hours_ago = [(now - t.sold_at) / timedelta(hours=1) for t in trades]
    assert min(hours_ago) >= 0
    assert max(hours_ago) <= 24 * 30 + 1


def test_listing_titles_combine_model_and_number() -> None:
    listings = make_listings()
    for it in listings[:10]:
        assert "#" in it["title"]
        assert it["model"] in it["title"]


def test_listings_per_collection_matches_argument() -> None:
    n = 5
    listings = make_listings(per_collection=n)
    counts: dict[str, int] = {}
    for x in listings:
        counts[x["collection"]] = counts.get(x["collection"], 0) + 1
    for c in COLLECTIONS:
        assert counts[c["name"]] == n


def test_unique_listing_ids() -> None:
    listings = make_listings(per_collection=12)
    ids = [x["id"] for x in listings]
    assert len(ids) == len(set(ids))
