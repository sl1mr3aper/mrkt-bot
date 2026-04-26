"""Lightweight in-process metrics tracker.

We don't ship a Prometheus exporter (the bot is single-instance and runs in
DRY-RUN mostly), but having visibility into key counters/histograms in memory
helps operators inspect health via the bot's <code>/health</code> command and
the daily analytics report.

Counters: monotonic integers (e.g. ``buy_attempt_total``).
Gauges: instantaneous values (e.g. ``ton_balance``).
Histograms: simple aggregation (count, sum, min, max, avg) without explicit
buckets — enough for "what's the average HTTP latency over the last hour".

The tracker is deliberately thread-/task-safe via a single asyncio lock since
all writes happen from inside a single event loop. It is *not* persisted —
restarts reset all counters, which is acceptable for short-running operations.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import monotonic
from typing import Any


@dataclass
class _Histogram:
    count: int = 0
    total: float = 0.0
    min_v: float | None = None
    max_v: float | None = None

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.min_v = value if self.min_v is None else min(self.min_v, value)
        self.max_v = value if self.max_v is None else max(self.max_v, value)

    @property
    def avg(self) -> float:
        return (self.total / self.count) if self.count else 0.0


@dataclass
class MetricsSnapshot:
    counters: dict[str, int]
    gauges: dict[str, float]
    histograms: dict[str, dict[str, float]]
    uptime_seconds: float


class MetricsRegistry:
    """Singleton-ish metrics container.

    Use ``MetricsRegistry.global_()`` everywhere instead of constructing your
    own to avoid scattered state.
    """

    _global: MetricsRegistry | None = None

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._hists: dict[str, _Histogram] = {}
        self._lock = asyncio.Lock()
        self._started = monotonic()

    @classmethod
    def global_(cls) -> MetricsRegistry:
        if cls._global is None:
            cls._global = cls()
        return cls._global

    async def incr(self, name: str, by: int = 1) -> None:
        async with self._lock:
            self._counters[name] = self._counters.get(name, 0) + by

    def incr_sync(self, name: str, by: int = 1) -> None:
        """Lock-free version for use inside non-async code paths."""
        self._counters[name] = self._counters.get(name, 0) + by

    async def gauge(self, name: str, value: float) -> None:
        async with self._lock:
            self._gauges[name] = float(value)

    def gauge_sync(self, name: str, value: float) -> None:
        self._gauges[name] = float(value)

    async def observe(self, name: str, value: float) -> None:
        async with self._lock:
            hist = self._hists.setdefault(name, _Histogram())
            hist.observe(float(value))

    def observe_sync(self, name: str, value: float) -> None:
        hist = self._hists.setdefault(name, _Histogram())
        hist.observe(float(value))

    def snapshot(self) -> MetricsSnapshot:
        return MetricsSnapshot(
            counters=dict(self._counters),
            gauges=dict(self._gauges),
            histograms={
                name: {
                    "count": h.count,
                    "sum": round(h.total, 4),
                    "min": h.min_v if h.min_v is not None else 0.0,
                    "max": h.max_v if h.max_v is not None else 0.0,
                    "avg": round(h.avg, 4),
                }
                for name, h in self._hists.items()
            },
            uptime_seconds=monotonic() - self._started,
        )

    def render(self) -> str:
        snap = self.snapshot()
        lines = [
            "📊 <b>Metrics</b>",
            f"Uptime: <b>{int(snap.uptime_seconds)}s</b>",
            "",
        ]
        if snap.counters:
            lines.append("<b>Counters</b>")
            for name, value in sorted(snap.counters.items()):
                lines.append(f"• <code>{name}</code>: {value}")
            lines.append("")
        if snap.gauges:
            lines.append("<b>Gauges</b>")
            for name, value in sorted(snap.gauges.items()):
                lines.append(f"• <code>{name}</code>: {value:.4f}")
            lines.append("")
        if snap.histograms:
            lines.append("<b>Histograms</b>")
            for name, hist in sorted(snap.histograms.items()):
                lines.append(
                    f"• <code>{name}</code> "
                    f"n={hist['count']} avg={hist['avg']:.4f} "
                    f"min={hist['min']:.4f} max={hist['max']:.4f}"
                )
        return "\n".join(lines)


@dataclass
class TimingContext:
    """``async with metrics.timed("name"):`` helper."""

    registry: MetricsRegistry
    name: str
    started: float = field(default=0.0)

    async def __aenter__(self) -> TimingContext:
        self.started = monotonic()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        elapsed = monotonic() - self.started
        await self.registry.observe(self.name, elapsed)


def timed(name: str) -> TimingContext:
    return TimingContext(MetricsRegistry.global_(), name)
