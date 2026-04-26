"""Manual market search and gift detail."""

from __future__ import annotations

import json

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from bot.states import SearchSG
from db.database import Database
from db.models import UserFilter
from utils.formatters import fmt_rarity, fmt_ton

router = Router(name="search")


@router.callback_query(F.data == "menu:orders")
async def cb_open_orders(cb: CallbackQuery, state: FSMContext, db: Database, engine, user) -> None:
    orders = await engine.orders.list_active(user.id)
    if cb.message is None:
        return
    if not orders:
        await cb.message.edit_text(
            "📭 Активных ордеров нет.",
            reply_markup=_back(),
        )
        await cb.answer()
        return
    lines = ["📊 <b>Активные ордера</b>", ""]
    for o in orders[:30]:
        lines.append(
            f"{'🟢 buy' if o.order_type == 'buy' else '🔴 sell'} "
            f"<code>{(o.gift_name or o.gift_id or '')[:24]}</code> "
            f"@ {fmt_ton(o.price)}"
        )
    await cb.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=_back())
    await cb.answer()


@router.callback_query(F.data == "menu:portfolio")
async def cb_open_portfolio(
    cb: CallbackQuery, state: FSMContext, db: Database, engine, user
) -> None:
    from db.repositories import PortfolioRepository

    async with db.session() as sess:
        items = await PortfolioRepository(sess).list_by_user(user.id)
    if cb.message is None:
        return
    if not items:
        await cb.message.edit_text("💼 Портфель пуст.", reply_markup=_back())
        await cb.answer()
        return
    lines = ["💼 <b>Портфель</b>", ""]
    for item in items[:30]:
        lines.append(
            f"<code>{(item.gift_name or '')[:18]}</code> "
            f"купл {fmt_ton(item.buy_price)} → цель {fmt_ton(item.target_sell)} "
            f"⭐ {fmt_rarity(item.rarity_score)}"
        )
    if len(items) > 30:
        lines.append(f"\n<i>… и ещё {len(items) - 30} позиций</i>")
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 Аналитика портфеля", callback_data="analytics:portfolio")
    kb.button(text="💾 Экспорт CSV", callback_data="portfolio:export")
    kb.button(text="🏠 Главное меню", callback_data="menu:main")
    kb.adjust(1)
    await cb.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=kb.as_markup())
    await cb.answer()


@router.callback_query(SearchSG.results)
async def cb_results_noop(cb: CallbackQuery) -> None:
    await cb.answer()


def _back():
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главное меню", callback_data="menu:main")
    return kb.as_markup()


async def _load_filter_dict(db: Database, user_id: int) -> dict[str, object]:
    async with db.session() as sess:
        result = await sess.execute(
            select(UserFilter).where(UserFilter.user_id == user_id).limit(1)
        )
        f = result.scalar_one_or_none()
    if not f:
        return {}
    try:
        return {
            "collection_names": json.loads(f.collection_names or "[]"),
            "model_names": json.loads(f.model_names or "[]"),
            "backdrop_names": json.loads(f.backdrop_names or "[]"),
            "symbol_names": json.loads(f.symbol_names or "[]"),
            "min_price_ton": f.min_price,
            "max_price_ton": f.max_price,
            "ordering": f.ordering or "Price",
            "low_to_high": f.low_to_high,
            "mintable": f.mintable_only or None,
            "number": f.number_filter,
        }
    except json.JSONDecodeError:
        return {}
