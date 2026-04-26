"""Tracks daily / all-time profit, fed by trade events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime


@dataclass
class ProfitStats:
    daily_profit: float = 0.0
    all_time_profit: float = 0.0
    daily_trades: int = 0
    daily_profitable: int = 0
    daily_losing: int = 0
    daily_breakeven: int = 0
    daily_stop_losses: int = 0
    last_reset_day: date = field(default_factory=lambda: datetime.now(UTC).date())


class ProfitTracker:
    def __init__(self) -> None:
        self.stats = ProfitStats()

    def _maybe_reset(self) -> None:
        today = datetime.now(UTC).date()
        if today != self.stats.last_reset_day:
            self.stats.daily_profit = 0.0
            self.stats.daily_trades = 0
            self.stats.daily_profitable = 0
            self.stats.daily_losing = 0
            self.stats.daily_breakeven = 0
            self.stats.daily_stop_losses = 0
            self.stats.last_reset_day = today

    def record_trade(
        self,
        *,
        net_profit: float,
        is_stop_loss: bool = False,
        breakeven_threshold: float = 0.001,
    ) -> None:
        self._maybe_reset()
        self.stats.daily_profit = round(self.stats.daily_profit + net_profit, 4)
        self.stats.all_time_profit = round(self.stats.all_time_profit + net_profit, 4)
        self.stats.daily_trades += 1
        if abs(net_profit) <= breakeven_threshold:
            self.stats.daily_breakeven += 1
        elif net_profit > 0:
            self.stats.daily_profitable += 1
        else:
            self.stats.daily_losing += 1
        if is_stop_loss:
            self.stats.daily_stop_losses += 1

    def set_all_time(self, value: float) -> None:
        self.stats.all_time_profit = round(value, 4)
