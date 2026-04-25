"""Inline keyboard helpers."""

from __future__ import annotations

from collections.abc import Iterable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb(*, dry_run: bool, auto: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Поиск/Фильтры", callback_data="menu:search")
    kb.button(text="💼 Портфель", callback_data="menu:portfolio")
    kb.button(text="🤖 Стратегии", callback_data="menu:strategies")
    kb.button(text="📊 Активные ордера", callback_data="menu:orders")
    kb.button(text="📈 Аналитика", callback_data="menu:analytics")
    kb.button(text="⚙️ Настройки", callback_data="menu:settings")
    kb.button(
        text=("🔴 DRY-RUN: ON" if dry_run else "🟢 DRY-RUN: OFF"),
        callback_data="dry_run:toggle",
    )
    kb.button(
        text=("⏸ Авто: ON" if auto else "▶️ Авто: OFF"),
        callback_data="auto:toggle",
    )
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()


def settings_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛡 Стоп-лосс %", callback_data="set:stop_loss")
    kb.button(text="💰 Макс. покупка", callback_data="set:max_buy")
    kb.button(text="📈 Мин. прибыль", callback_data="set:min_profit")
    kb.button(text="🎯 Крупная сделка", callback_data="set:large_deal")
    kb.button(text="🌐 Прокси", callback_data="set:proxy")
    kb.button(text="🔔 Уведомления", callback_data="set:notifications")
    kb.button(text="🧪 DRY-RUN", callback_data="set:dry_run")
    kb.button(text="🏠 Главное меню", callback_data="menu:main")
    kb.adjust(2, 2, 2, 2)
    return kb.as_markup()


def confirm_kb(yes_data: str, no_data: str = "menu:main") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=yes_data)
    kb.button(text="❌ Отмена", callback_data=no_data)
    kb.adjust(2)
    return kb.as_markup()


def analytics_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Топ‑прибыль", callback_data="analytics:gainers")
    kb.button(text="📉 Топ‑убытки", callback_data="analytics:losers")
    kb.button(text="💧 Ликвидность", callback_data="analytics:liquidity")
    kb.button(text="📊 График floor", callback_data="analytics:chart_floor")
    kb.button(text="📈 P&L график", callback_data="analytics:chart_pnl")
    kb.button(text="🏠 Главное меню", callback_data="menu:main")
    kb.adjust(2, 2, 2)
    return kb.as_markup()


def strategy_list_kb(items: Iterable[tuple[int, str, bool]]) -> InlineKeyboardMarkup:
    """`items` — iterable of (id, name, is_active)."""
    kb = InlineKeyboardBuilder()
    for sid, name, active in items:
        prefix = "🟢" if active else "⚪️"
        kb.button(text=f"{prefix} {name}", callback_data=f"strategy:open:{sid}")
    kb.button(text="➕ Новая стратегия", callback_data="strategy:new")
    kb.button(text="🏠 Главное меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def back_button(target: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="↩️ Назад", callback_data=target)]]
    )
