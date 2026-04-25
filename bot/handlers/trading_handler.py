"""Trading dashboard."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.states import TradingSG
from db.database import Database
from db.repositories import TradeRepository
from utils.formatters import fmt_ton

router = Router(name="trading")


def _trading_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Активные ордера", callback_data="menu:orders")
    kb.button(text="💼 Портфель", callback_data="menu:portfolio")
    kb.button(text="🤖 Стратегии", callback_data="menu:strategies")
    kb.button(text="🏠 Главное меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


@router.callback_query(F.data == "menu:trading")
async def cb_trading(
    cb: CallbackQuery, state: FSMContext, db: Database, engine, user
) -> None:
    await state.set_state(TradingSG.dashboard)
    async with db.session() as sess:
        stats = await TradeRepository(sess).daily_stats(user.id)
        all_time = await TradeRepository(sess).all_time_profit(user.id)
    text = (
        "📈 <b>Торговля</b>\n\n"
        f"💼 Баланс: {fmt_ton(engine.market.balance_ton)}\n"
        f"📊 Сделок сегодня: {stats['count']}\n"
        f"💰 Прибыль сегодня: {fmt_ton(stats['net'], sign=True)}\n"
        f"🏆 Прибыль всего: {fmt_ton(all_time, sign=True)}\n"
    )
    if cb.message is not None:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=_trading_kb())
    await cb.answer()
