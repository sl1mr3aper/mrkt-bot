"""Matplotlib chart helpers — rendered to in-memory PNGs."""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import datetime

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    HAS_MPL = True
except Exception:  # pragma: no cover - matplotlib optional in some envs
    HAS_MPL = False


def _new_figure() -> plt.Figure:  # type: ignore[name-defined]
    if not HAS_MPL:
        raise RuntimeError("matplotlib not available in environment")
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    ax.grid(True, linestyle=":", linewidth=0.6, alpha=0.5)
    return fig


def _figure_to_bytes(fig: plt.Figure) -> bytes:  # type: ignore[name-defined]
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def render_floor_chart(
    title: str, dates: Sequence[datetime], floors: Sequence[float]
) -> bytes:
    """Floor-price-over-time line chart."""
    if not HAS_MPL:
        return b""
    fig = _new_figure()
    ax = fig.gca()
    ax.plot(dates, floors, marker="o", linewidth=1.6)
    ax.set_title(title)
    ax.set_xlabel("Время")
    ax.set_ylabel("Floor (TON)")
    fig.autofmt_xdate()
    return _figure_to_bytes(fig)


def render_pnl_chart(
    title: str, dates: Sequence[datetime], net_profits: Sequence[float]
) -> bytes:
    """Cumulative P&L bar chart."""
    if not HAS_MPL:
        return b""
    fig = _new_figure()
    ax = fig.gca()
    cumulative: list[float] = []
    total = 0.0
    for value in net_profits:
        total += value
        cumulative.append(total)
    colors = ["#3a9d3a" if v >= 0 else "#cc4444" for v in net_profits]
    ax.bar(range(len(net_profits)), net_profits, color=colors, alpha=0.6)
    ax.plot(range(len(cumulative)), cumulative, color="#2a59c4", linewidth=2.2)
    ax.set_title(title)
    ax.set_xlabel("Сделка")
    ax.set_ylabel("P&L (TON)")
    return _figure_to_bytes(fig)
