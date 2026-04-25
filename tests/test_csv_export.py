"""Tests for the CSV export helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from utils.csv_export import (
    export_collections,
    export_portfolio,
    export_price_history,
    export_trades,
)


@dataclass
class _Trade:
    id: int
    gift_name: str
    collection: str
    buy_price: float
    sell_price: float
    commission: float
    gross_profit: float
    net_profit: float
    profit_pct: float
    hold_time_sec: int
    dry_run: bool
    sold_at: datetime


def test_export_trades_has_bom_and_header() -> None:
    rows = [
        _Trade(1, "Pepe #1", "PlushPepe", 1.0, 1.5, 0.05, 0.5, 0.45, 45.0, 3600, True,
               datetime(2024, 1, 5, 12, 0, tzinfo=UTC)),
    ]
    blob = export_trades(rows)
    assert blob.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM
    text = blob.decode("utf-8")
    assert "gift_name" in text
    assert "Pepe #1" in text
    assert "PlushPepe" in text


@dataclass
class _Item:
    id: int
    gift_name: str
    collection: str
    buy_price: float
    rarity_score: float
    bought_at: datetime


def test_export_portfolio_writes_all_columns() -> None:
    rows = [
        _Item(1, "Plush", "PP", 1.5, 8.4, datetime(2024, 1, 1, 10, 0, tzinfo=UTC)),
        _Item(2, "Cap", "DC", 4.0, 25.0, datetime(2024, 1, 2, 11, 0, tzinfo=UTC)),
    ]
    blob = export_portfolio(rows)
    text = blob.decode("utf-8")
    assert text.count("\n") >= 2
    assert "Plush" in text
    assert "rarity_score" in text


@dataclass
class _Price:
    collection: str
    floor_price: float | None
    median_price: float | None
    min_price: float | None
    max_price: float | None
    avg_price: float | None
    volume_count: int
    recorded_at: datetime


def test_export_price_history() -> None:
    rows = [
        _Price("PP", 1.0, 1.2, 0.9, 1.5, 1.1, 12, datetime.now(UTC)),
    ]
    blob = export_price_history(rows)
    text = blob.decode("utf-8")
    assert "collection" in text
    assert "PP" in text


def test_export_collections() -> None:
    @dataclass
    class _Snap:
        name: str
        title: str
        floor_price: float
        previous_floor: float
        volume: float
        listings: list
        sales_24h: int

    snaps = [_Snap("PP", "Plush Pepe", 1.0, 1.05, 1234.0, [{}, {}, {}], 5)]
    blob = export_collections(snaps)
    text = blob.decode("utf-8")
    assert "Plush Pepe" in text
    # Listings count should be 3
    assert ";3;" in text


def test_empty_inputs_only_have_header() -> None:
    blob = export_trades([])
    text = blob.decode("utf-8")
    assert text.count("\n") == 1  # only header line
