"""Textual analytics reports (markdown / HTML for Telegram)."""

from __future__ import annotations

from datetime import UTC, datetime

from utils.formatters import fmt_pct, fmt_ton


def daily_report(
    *,
    date: datetime,
    daily_profit: float,
    all_time_profit: float,
    balance: float,
    total_trades: int,
    profitable: int,
    breakeven: int,
    losing: int,
    stop_losses: int,
    best_trade_text: str | None = None,
    worst_trade_text: str | None = None,
    portfolio_size: int = 0,
    portfolio_value: float = 0.0,
    active_strategies: int = 0,
) -> str:
    profit_pct_str = (
        fmt_pct((profitable / total_trades) * 100.0, sign=False)
        if total_trades
        else "—"
    )
    return (
        "📊 <b>ЕЖЕДНЕВНЫЙ ОТЧЁТ</b>\n\n"
        f"📅 {date.strftime('%d %B %Y')}\n\n"
        "💰 <b>ФИНАНСЫ</b>\n"
        f"   Прибыль сегодня: {fmt_ton(daily_profit, sign=True)}\n"
        f"   Прибыль всего:  {fmt_ton(all_time_profit, sign=True)}\n"
        f"   Текущий баланс: {fmt_ton(balance)}\n\n"
        f"📈 <b>СДЕЛКИ:</b> {total_trades}\n"
        f"   ✅ Прибыльных: {profitable} ({profit_pct_str})\n"
        f"   ➖ В ноль:     {breakeven}\n"
        f"   ❌ Убыточных:  {losing}\n"
        f"   🚨 Стоп-лосс:  {stop_losses}\n\n"
        f"🏆 Лучшая: {best_trade_text or '—'}\n"
        f"📉 Худшая: {worst_trade_text or '—'}\n\n"
        f"💼 Портфель: {portfolio_size} шт. (~{fmt_ton(portfolio_value)})\n"
        f"📊 Активных стратегий: {active_strategies}"
    )


def now_utc() -> datetime:
    return datetime.now(UTC)
