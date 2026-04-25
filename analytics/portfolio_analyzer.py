"""Portfolio-level analytics: unrealised P&L, exposure by collection,
average holding time, biggest open winners/losers.

Operates on the active ``PortfolioItem`` rows for a user combined with the
in-memory ``MarketState`` floor cache.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import mean
from typing import Any


@dataclass
class PortfolioPosition:
    item_id: int
    gift_name: str
    collection: str
    buy_price: float
    current_floor: float
    unrealised_profit: float
    unrealised_pct: float
    hold_seconds: int


@dataclass
class PortfolioReport:
    positions: list[PortfolioPosition]
    total_invested: float
    total_value_now: float
    unrealised_pnl: float
    unrealised_pct: float
    avg_hold_hours: float
    by_collection: dict[str, float]   # exposure (TON) per collection
    biggest_winner: PortfolioPosition | None
    biggest_loser: PortfolioPosition | None


class PortfolioAnalyzer:
    """Compute a ``PortfolioReport`` from a list of portfolio items + market."""

    @staticmethod
    def analyse(
        items: list[Any],
        *,
        floors: dict[str, float],
    ) -> PortfolioReport:
        positions: list[PortfolioPosition] = []
        now = datetime.now(UTC)
        for item in items:
            buy_price = float(getattr(item, "buy_price", 0.0) or 0.0)
            collection = getattr(item, "collection", "")
            current_floor = float(floors.get(collection, 0.0) or 0.0)
            unrealised = round(current_floor - buy_price, 4) if current_floor else 0.0
            unrealised_pct = round(
                (unrealised / buy_price * 100.0) if buy_price else 0.0, 2
            )
            bought_at = getattr(item, "bought_at", None)
            hold_sec = (
                int((now - bought_at).total_seconds())
                if bought_at is not None
                else 0
            )
            positions.append(
                PortfolioPosition(
                    item_id=getattr(item, "id", 0),
                    gift_name=getattr(item, "gift_name", "?"),
                    collection=collection,
                    buy_price=buy_price,
                    current_floor=current_floor,
                    unrealised_profit=unrealised,
                    unrealised_pct=unrealised_pct,
                    hold_seconds=hold_sec,
                )
            )
        total_invested = round(sum(p.buy_price for p in positions), 4)
        total_value_now = round(sum(p.current_floor for p in positions), 4)
        unrealised_pnl = round(total_value_now - total_invested, 4)
        unrealised_pct = round(
            (unrealised_pnl / total_invested * 100.0) if total_invested else 0.0, 2
        )
        avg_hold_hours = round(
            mean(p.hold_seconds / 3600.0 for p in positions) if positions else 0.0,
            2,
        )
        by_collection: dict[str, float] = {}
        for p in positions:
            by_collection[p.collection] = round(
                by_collection.get(p.collection, 0.0) + p.buy_price, 4
            )
        biggest_winner: PortfolioPosition | None = None
        biggest_loser: PortfolioPosition | None = None
        for p in positions:
            if biggest_winner is None or p.unrealised_profit > biggest_winner.unrealised_profit:
                biggest_winner = p
            if biggest_loser is None or p.unrealised_profit < biggest_loser.unrealised_profit:
                biggest_loser = p
        return PortfolioReport(
            positions=positions,
            total_invested=total_invested,
            total_value_now=total_value_now,
            unrealised_pnl=unrealised_pnl,
            unrealised_pct=unrealised_pct,
            avg_hold_hours=avg_hold_hours,
            by_collection=by_collection,
            biggest_winner=biggest_winner,
            biggest_loser=biggest_loser,
        )

    @staticmethod
    def render(report: PortfolioReport) -> str:
        lines = [
            "💼 <b>Portfolio Analytics</b>",
            "",
            f"Позиций: <b>{len(report.positions)}</b>",
            f"Инвестировано: <b>{report.total_invested:.3f}</b> TON",
            f"Текущая стоимость: <b>{report.total_value_now:.3f}</b> TON",
            f"Неreal P&L: <b>{report.unrealised_pnl:+.3f}</b> TON ({report.unrealised_pct:+.2f}%)",
            f"Средний холд: <b>{report.avg_hold_hours:.1f}ч</b>",
        ]
        if report.biggest_winner:
            w = report.biggest_winner
            lines.append("")
            lines.append(
                f"🥇 Лидер: <code>{w.gift_name[:24]}</code> "
                f"({w.unrealised_pct:+.1f}%, {w.unrealised_profit:+.3f} TON)"
            )
        if report.biggest_loser and report.biggest_loser is not report.biggest_winner:
            lo = report.biggest_loser
            lines.append(
                f"🔻 Аутсайдер: <code>{lo.gift_name[:24]}</code> "
                f"({lo.unrealised_pct:+.1f}%, {lo.unrealised_profit:+.3f} TON)"
            )
        if report.by_collection:
            lines.append("")
            lines.append("<b>Экспозиция:</b>")
            top = sorted(report.by_collection.items(), key=lambda kv: kv[1], reverse=True)[:8]
            for coll, ton in top:
                lines.append(f"• <code>{coll[:18]:<18}</code> {ton:.3f} TON")
        return "\n".join(lines)
