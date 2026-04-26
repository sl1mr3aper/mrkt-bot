"""Lightweight strategy backtester.

The backtester is *not* a full event-driven simulator — it's a deterministic
walk over a list of historical listings using the strategy's ``should_buy``
hook. Used for quick what-if analysis from the bot UI ("backtest this strategy
on yesterday's snapshot") and from unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean, median
from typing import Any

from strategies.base import BaseStrategy


@dataclass
class BacktestTrade:
    gift_id: str
    gift_name: str
    collection: str
    buy_price: float
    sell_price: float
    profit: float
    profit_pct: float
    reason: str


@dataclass
class BacktestReport:
    strategy_name: str
    candidates_seen: int
    trades: list[BacktestTrade] = field(default_factory=list)
    skipped_reasons: dict[str, int] = field(default_factory=dict)

    @property
    def trades_count(self) -> int:
        return len(self.trades)

    @property
    def total_profit(self) -> float:
        return round(sum(t.profit for t in self.trades), 4)

    @property
    def win_rate(self) -> float:
        wins = sum(1 for t in self.trades if t.profit > 0)
        return wins / self.trades_count if self.trades_count else 0.0

    @property
    def avg_profit_pct(self) -> float:
        if not self.trades:
            return 0.0
        return round(mean(t.profit_pct for t in self.trades), 2)

    @property
    def median_profit_pct(self) -> float:
        if not self.trades:
            return 0.0
        return round(median(t.profit_pct for t in self.trades), 2)

    def render(self) -> str:
        return (
            f"Стратегия: {self.strategy_name}\n"
            f"Просмотрено листингов: {self.candidates_seen}\n"
            f"Совершено сделок: {self.trades_count}\n"
            f"Win-rate: {self.win_rate * 100:.1f}%\n"
            f"Средняя прибыль: {self.avg_profit_pct}%\n"
            f"Медианная прибыль: {self.median_profit_pct}%\n"
            f"Суммарный профит: {self.total_profit:+.3f} TON"
        )


@dataclass
class _Analysis:
    floor: float
    rarity_score: float
    cluster_size_at_floor: int = 5
    spread_pct: float = 1.0
    fair_value: float = 0.0


class BacktestEngine:
    """Replays a list of listings against a strategy.

    The engine assumes a simplistic price evolution: each "buy" is settled
    by selling at ``buy_price * sell_multiplier`` (read from strategy params,
    default 1.15). Commissions are taken from ``commission_pct`` (default 5%).
    """

    def __init__(self, *, commission_pct: float = 0.05) -> None:
        self.commission_pct = commission_pct

    def run(
        self,
        strategy: BaseStrategy,
        listings: list[dict[str, Any]],
        *,
        floor_history: list[float] | None = None,
    ) -> BacktestReport:
        report = BacktestReport(
            strategy_name=getattr(strategy, "display_name", strategy.type_id),
            candidates_seen=len(listings),
        )
        sell_multiplier = float(strategy.params.get("sell_multiplier", 1.15))
        user_state = {
            "commission": self.commission_pct,
            "market_listings": listings,
            "floor_history": floor_history or [],
        }
        for gift in listings:
            analysis = _Analysis(
                floor=float(gift.get("floor_price") or gift.get("price") or 0.0),
                rarity_score=float(gift.get("rarity_score") or 100.0),
                cluster_size_at_floor=int(gift.get("cluster_size_at_floor") or 5),
                spread_pct=float(gift.get("spread_pct") or 1.0),
                fair_value=float(gift.get("fair_value") or 0.0),
            )
            decision = strategy.should_buy(
                gift=gift, analysis=analysis, user_state=user_state
            )
            if not decision.should_buy:
                reason = decision.reason or "skip"
                report.skipped_reasons[reason] = report.skipped_reasons.get(reason, 0) + 1
                continue
            buy = float(gift.get("price") or 0.0)
            sell = round(buy * sell_multiplier, 4)
            commission = round(sell * self.commission_pct, 4)
            profit = round(sell - buy - commission, 4)
            profit_pct = round((profit / buy * 100.0) if buy else 0.0, 2)
            report.trades.append(
                BacktestTrade(
                    gift_id=str(gift.get("id") or ""),
                    gift_name=str(gift.get("title") or gift.get("name") or ""),
                    collection=str(gift.get("collection") or ""),
                    buy_price=buy,
                    sell_price=sell,
                    profit=profit,
                    profit_pct=profit_pct,
                    reason=decision.reason or "buy",
                )
            )
        return report
