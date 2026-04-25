"""User-facing message formatters (Telegram HTML)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

# ─── Helpers ────────────────────────────────────────────────


def fmt_ton(value: float | int | None, *, decimals: int = 2, sign: bool = False) -> str:
    """Format TON value: ``2.36 TON`` / ``+1.25 TON``."""
    if value is None:
        return "—"
    formatted = f"{value:+.{decimals}f}" if sign else f"{value:.{decimals}f}"
    return f"{formatted} TON"


def fmt_pct(value: float | None, *, decimals: int = 1, sign: bool = True) -> str:
    if value is None:
        return "—"
    return f"{value:+.{decimals}f}%" if sign else f"{value:.{decimals}f}%"


def fmt_dt(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M:%S")


def fmt_rarity(score: float | None) -> str:
    if score is None:
        return "—"
    label = rarity_label(score)
    return f"{score:.1f}/10 ({label})"


def rarity_label(score: float) -> str:
    if score >= 9.5:
        return "Legendary"
    if score >= 8.5:
        return "Epic"
    if score >= 7.0:
        return "Rare"
    if score >= 5.5:
        return "Uncommon"
    if score >= 4.0:
        return "Common+"
    return "Common"


def safe_collection(name: str | None) -> str:
    return name or "Unknown"


# ─── Notification builders ─────────────────────────────────


def fmt_buy_success(data: dict[str, Any]) -> str:
    """✅ ПОКУПКА ВЫПОЛНЕНА template."""
    return (
        "✅ <b>ПОКУПКА ВЫПОЛНЕНА</b>\n\n"
        f"🎁 <b>{data.get('gift_name', '—')}</b>\n"
        f"📦 Коллекция: {safe_collection(data.get('collection'))}\n"
        f"🎨 Model: {data.get('model','—')} [{fmt_pct(data.get('model_pct'), sign=False)}]\n"
        f"🖼 Backdrop: {data.get('backdrop','—')} [{fmt_pct(data.get('backdrop_pct'), sign=False)}]\n"
        f"💎 Symbol: {data.get('symbol','—')} [{fmt_pct(data.get('symbol_pct'), sign=False)}]\n"
        f"⭐ Rarity: {fmt_rarity(data.get('rarity_score'))}\n"
        f"🔢 Номер: #{data.get('number','—')}\n\n"
        f"💰 Куплено по: <b>{fmt_ton(data.get('buy_price'))}</b>\n"
        f"🎯 Целевая продажа: {fmt_ton(data.get('target_sell'))}\n"
        f"📈 Прогноз прибыли: {fmt_ton(data.get('expected_profit'), sign=True)} "
        f"({fmt_pct(data.get('expected_profit_pct'))})\n"
        f"⏱ Cooldown: {data.get('cooldown_sec', 60)} сек\n"
        f"💼 Баланс: {fmt_ton(data.get('balance_after'))}\n\n"
        f"🤖 Стратегия: {data.get('strategy','—')}\n"
        f"⏰ {fmt_dt(data.get('time'))}"
    )


def fmt_listed(data: dict[str, Any]) -> str:
    """📋 ВЫСТАВЛЕНО НА ПРОДАЖУ template."""
    return (
        "📋 <b>ВЫСТАВЛЕНО НА ПРОДАЖУ</b>\n\n"
        f"🎁 <b>{data.get('gift_name','—')}</b>\n"
        f"⭐ Rarity: {fmt_rarity(data.get('rarity_score'))}\n\n"
        f"💰 Куплено: {fmt_ton(data.get('buy_price'))}\n"
        f"💵 Цена продажи: <b>{fmt_ton(data.get('sell_price'))}</b>\n"
        f"📈 Потенциальная прибыль: {fmt_ton(data.get('expected_profit'), sign=True)} "
        f"({fmt_pct(data.get('expected_profit_pct'))})\n"
        f"🛡 Стоп-лосс: {fmt_ton(data.get('stop_loss_price'))}\n\n"
        f"⏰ {fmt_dt(data.get('time'))}"
    )


def fmt_sell_success(data: dict[str, Any]) -> str:
    """💰 ПРОДАЖА СОВЕРШЕНА template."""
    return (
        "💰 <b>ПРОДАЖА СОВЕРШЕНА</b>\n\n"
        f"🎁 <b>{data.get('gift_name','—')}</b>\n"
        f"⭐ Rarity: {fmt_rarity(data.get('rarity_score'))}\n\n"
        f"💸 Куплено: {fmt_ton(data.get('buy_price'))}\n"
        f"💵 Продано: {fmt_ton(data.get('sell_price'))}\n"
        f"💳 Комиссия: {fmt_ton(-(data.get('commission') or 0), sign=True)}\n"
        f"✅ <b>ЧИСТАЯ ПРИБЫЛЬ:</b> {fmt_ton(data.get('net_profit'), sign=True)} "
        f"({fmt_pct(data.get('profit_pct'))})\n"
        f"⏱ Время удержания: {data.get('hold_time_human','—')}\n"
        f"💼 Баланс: {fmt_ton(data.get('balance_after'))}\n\n"
        f"📊 Прибыль сегодня: {fmt_ton(data.get('daily_profit'), sign=True)}\n"
        f"📈 Прибыль всего: {fmt_ton(data.get('all_time_profit'), sign=True)}\n\n"
        f"⏰ {fmt_dt(data.get('time'))}"
    )


def fmt_stop_loss(data: dict[str, Any]) -> str:
    return (
        "🚨 <b>СТОП-ЛОСС СРАБОТАЛ</b>\n\n"
        f"🎁 <b>{data.get('gift_name','—')}</b>\n\n"
        "📉 Ситуация:\n"
        f"   Цена покупки: {fmt_ton(data.get('buy_price'))}\n"
        f"   Текущий floor: {fmt_ton(data.get('current_floor'))} ({fmt_pct(data.get('floor_change_pct'))})\n"
        f"   Порог стоп-лосс: {fmt_ton(data.get('stop_threshold'))}\n\n"
        f"⚡ Действие: Продажа по {fmt_ton(data.get('sell_at'))}\n"
        f"💸 Убыток: {fmt_ton(data.get('loss'), sign=True)} ({fmt_pct(data.get('loss_pct'))})\n\n"
        f"💼 Баланс после: {fmt_ton(data.get('balance_after'))}\n"
        f"⏰ {fmt_dt(data.get('time'))}"
    )


def fmt_stuck_order(data: dict[str, Any]) -> str:
    minutes = int(data.get("age_min") or 5)
    return (
        f"⏰ <b>ОРДЕР НЕ ИСПОЛНЕН — {minutes} МИНУТ</b>\n\n"
        f"🎁 {data.get('gift_name','—')}\n"
        f"💰 Цена продажи: {fmt_ton(data.get('sell_price'))}\n"
        f"📊 Текущий floor: {fmt_ton(data.get('current_floor'))}\n"
        f"⚡ Ваш ордер выше floor на {fmt_pct(data.get('above_floor_pct'))}\n\n"
        "Что делать?"
    )


def fmt_dry_run(data: dict[str, Any]) -> str:
    return (
        "🧪 <b>DRY RUN — СИМУЛЯЦИЯ</b>\n\n"
        f"🎁 <b>{data.get('gift_name','—')}</b>\n"
        f"💰 Купил бы по: {fmt_ton(data.get('buy_price'))}\n"
        f"📈 Прогноз прибыли: {fmt_ton(data.get('expected_profit'), sign=True)} "
        f"({fmt_pct(data.get('expected_profit_pct'))})\n\n"
        "<i>РЕАЛЬНАЯ СДЕЛКА НЕ СОВЕРШЕНА</i>\n"
        "Чтобы торговать — выключите DRY RUN в настройках\n\n"
        f"⏰ {fmt_dt(data.get('time'))}"
    )


def fmt_daily_report(data: dict[str, Any]) -> str:
    return (
        "📊 <b>ЕЖЕДНЕВНЫЙ ОТЧЁТ</b>\n\n"
        f"📅 {data.get('date_human','—')}\n\n"
        "💰 <b>ФИНАНСЫ:</b>\n"
        f"   Прибыль сегодня: {fmt_ton(data.get('daily_profit'), sign=True)}\n"
        f"   Прибыль всего: {fmt_ton(data.get('all_time_profit'), sign=True)}\n"
        f"   Текущий баланс: {fmt_ton(data.get('balance'))}\n\n"
        f"📈 <b>СДЕЛКИ СЕГОДНЯ:</b> {data.get('total_trades', 0)}\n"
        f"   ✅ Прибыльных: {data.get('profitable', 0)}\n"
        f"   ➖ В ноль: {data.get('breakeven', 0)}\n"
        f"   ❌ Убыточных: {data.get('losing', 0)}\n"
        f"   🚨 Стоп-лоссов: {data.get('stop_losses', 0)}\n"
    )


def fmt_main_menu_header(data: dict[str, Any]) -> str:
    dry = "🟢 ON" if data.get("dry_run") else "🔴 OFF"
    auto = "🟢 ON" if data.get("auto") else "⏸ OFF"
    return (
        "🏠 <b>Главное меню</b>\n\n"
        f"💼 Баланс: <b>{fmt_ton(data.get('balance'))}</b>\n"
        f"🧪 DRY RUN: {dry}\n"
        f"🤖 Авто-торговля: {auto}\n"
        f"📊 Прибыль сегодня: {fmt_ton(data.get('daily_profit', 0), sign=True)}"
    )


def fmt_human_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}с"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}мин {sec}с"
    hours, mins = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}ч {mins}мин"
    days, hrs = divmod(hours, 24)
    return f"{days}д {hrs}ч"
