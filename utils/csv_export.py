"""CSV export helpers for trades, portfolio and price history.

The functions return ``bytes`` with a UTF-8 BOM so the produced file opens
correctly in Excel and Google Sheets without manual encoding selection.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from datetime import datetime
from typing import Any


def _writer(buf: io.StringIO) -> csv.writer:
    return csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)


def _finalise(buf: io.StringIO) -> bytes:
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def export_trades(trades: Iterable[Any]) -> bytes:
    buf = io.StringIO()
    w = _writer(buf)
    w.writerow([
        "id",
        "gift_name",
        "collection",
        "buy_price",
        "sell_price",
        "commission",
        "gross_profit",
        "net_profit",
        "profit_pct",
        "hold_time_sec",
        "dry_run",
        "sold_at",
    ])
    for t in trades:
        w.writerow([
            getattr(t, "id", ""),
            getattr(t, "gift_name", ""),
            getattr(t, "collection", ""),
            getattr(t, "buy_price", ""),
            getattr(t, "sell_price", ""),
            getattr(t, "commission", ""),
            getattr(t, "gross_profit", ""),
            getattr(t, "net_profit", ""),
            getattr(t, "profit_pct", ""),
            getattr(t, "hold_time_sec", ""),
            "yes" if getattr(t, "dry_run", False) else "no",
            _fmt_dt(getattr(t, "sold_at", None)),
        ])
    return _finalise(buf)


def export_portfolio(items: Iterable[Any]) -> bytes:
    buf = io.StringIO()
    w = _writer(buf)
    w.writerow([
        "id",
        "gift_name",
        "collection",
        "buy_price",
        "rarity_score",
        "bought_at",
    ])
    for it in items:
        w.writerow([
            getattr(it, "id", ""),
            getattr(it, "gift_name", ""),
            getattr(it, "collection", ""),
            getattr(it, "buy_price", ""),
            getattr(it, "rarity_score", ""),
            _fmt_dt(getattr(it, "bought_at", None)),
        ])
    return _finalise(buf)


def export_price_history(rows: Iterable[Any]) -> bytes:
    buf = io.StringIO()
    w = _writer(buf)
    w.writerow([
        "collection",
        "floor_price",
        "median_price",
        "min_price",
        "max_price",
        "avg_price",
        "volume_count",
        "recorded_at",
    ])
    for r in rows:
        w.writerow([
            getattr(r, "collection", ""),
            getattr(r, "floor_price", ""),
            getattr(r, "median_price", ""),
            getattr(r, "min_price", ""),
            getattr(r, "max_price", ""),
            getattr(r, "avg_price", ""),
            getattr(r, "volume_count", ""),
            _fmt_dt(getattr(r, "recorded_at", None)),
        ])
    return _finalise(buf)


def export_collections(snapshots: Iterable[Any]) -> bytes:
    buf = io.StringIO()
    w = _writer(buf)
    w.writerow([
        "name",
        "title",
        "floor_price",
        "previous_floor",
        "volume_24h",
        "listings",
        "sales_24h",
    ])
    for s in snapshots:
        w.writerow([
            getattr(s, "name", ""),
            getattr(s, "title", ""),
            getattr(s, "floor_price", ""),
            getattr(s, "previous_floor", ""),
            getattr(s, "volume", ""),
            len(getattr(s, "listings", []) or []),
            getattr(s, "sales_24h", 0),
        ])
    return _finalise(buf)


def _fmt_dt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)
