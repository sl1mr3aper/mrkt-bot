"""Tests for the in-process metrics registry."""

from __future__ import annotations

import asyncio

import pytest

from core.metrics import MetricsRegistry, timed


def test_counter_increments_synchronously() -> None:
    reg = MetricsRegistry()
    reg.incr_sync("foo")
    reg.incr_sync("foo", by=4)
    snap = reg.snapshot()
    assert snap.counters["foo"] == 5


def test_gauge_replaces_value() -> None:
    reg = MetricsRegistry()
    reg.gauge_sync("ton_balance", 1.23)
    reg.gauge_sync("ton_balance", 4.56)
    assert reg.snapshot().gauges["ton_balance"] == 4.56


def test_histogram_records_min_max_avg() -> None:
    reg = MetricsRegistry()
    for v in [0.1, 0.2, 0.3]:
        reg.observe_sync("latency", v)
    snap = reg.snapshot().histograms["latency"]
    assert snap["count"] == 3
    assert pytest.approx(snap["min"], rel=1e-6) == 0.1
    assert pytest.approx(snap["max"], rel=1e-6) == 0.3
    assert pytest.approx(snap["avg"], rel=1e-3) == 0.2


def test_render_emits_human_friendly_text() -> None:
    reg = MetricsRegistry()
    reg.incr_sync("buys", 3)
    reg.gauge_sync("balance", 7.0)
    reg.observe_sync("latency", 0.05)
    out = reg.render()
    assert "Counters" in out
    assert "Gauges" in out
    assert "Histograms" in out
    assert "buys" in out


@pytest.mark.asyncio
async def test_timed_context_records_elapsed() -> None:
    reg = MetricsRegistry()
    MetricsRegistry._global = reg
    try:
        async with timed("op_total_seconds"):
            await asyncio.sleep(0.01)
    finally:
        MetricsRegistry._global = None
    snap = reg.snapshot().histograms["op_total_seconds"]
    assert snap["count"] == 1
    assert snap["avg"] >= 0.005


def test_global_singleton_is_consistent() -> None:
    a = MetricsRegistry.global_()
    b = MetricsRegistry.global_()
    assert a is b
