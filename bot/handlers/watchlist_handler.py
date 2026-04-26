"""Watchlist UI: add / list / toggle / delete floor-price alerts."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.common import cancel_kb
from db.database import Database
from db.repositories import WatchlistRepository
from utils.formatters import fmt_ton
from utils.validators import parse_ton_amount

router = Router(name="watchlist")


class WatchlistSG(StatesGroup):
    main = State()
    add_collection = State()
    add_price = State()
    add_direction = State()


def _menu_kb(items: list) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить алерт", callback_data="wl:add")
    for it in items[:20]:
        flag = "🟢" if it.is_active else "⚪️"
        arrow = "≤" if it.direction == "below" else "≥"
        kb.button(
            text=f"{flag} {it.collection} {arrow} {fmt_ton(it.target_price)}",
            callback_data=f"wl:open:{it.id}",
        )
    kb.button(text="↩️ В меню", callback_data="menu:main")
    kb.adjust(1)
    return kb


def _detail_kb(item_id: int, active: bool) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="⏸ Отключить" if active else "▶️ Включить",
        callback_data=f"wl:toggle:{item_id}",
    )
    kb.button(text="🗑 Удалить", callback_data=f"wl:delete:{item_id}")
    kb.button(text="↩️ К списку", callback_data="menu:watchlist")
    kb.adjust(2, 1)
    return kb


@router.callback_query(F.data == "menu:watchlist")
async def cb_open(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    await state.set_state(WatchlistSG.main)
    async with db.session() as sess:
        items = await WatchlistRepository(sess).list_by_user(user.id)
    text = (
        "🔔 <b>Watchlist</b>\n\n"
        "Алерты по floor-цене коллекций. "
        "Срабатывают раз в 10 минут (через market monitor)."
    )
    if cb.message is not None:
        await cb.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=_menu_kb(items).as_markup(),
        )
    await cb.answer()


@router.callback_query(F.data == "wl:add")
async def cb_add(cb: CallbackQuery, state: FSMContext, engine) -> None:
    await state.set_state(WatchlistSG.add_collection)
    coll_names = list(engine.market.collections.keys())[:30]
    kb = InlineKeyboardBuilder()
    for name in coll_names:
        kb.button(text=name, callback_data=f"wl:c:{name}")
    kb.button(text="↩️ Назад", callback_data="menu:watchlist")
    kb.adjust(2)
    if cb.message is not None:
        await cb.message.edit_text(
            "Выбери коллекцию для алерта:",
            reply_markup=kb.as_markup(),
        )
    await cb.answer()


@router.callback_query(F.data.startswith("wl:c:"))
async def cb_pick_collection(cb: CallbackQuery, state: FSMContext) -> None:
    name = (cb.data or "").split(":", 2)[-1]
    await state.update_data(collection=name)
    await state.set_state(WatchlistSG.add_price)
    if cb.message is not None:
        await cb.message.edit_text(
            f"Коллекция: <code>{name}</code>\n\n"
            "Введите целевую floor-цену в TON (например <code>1.5</code>):",
            parse_mode="HTML",
            reply_markup=cancel_kb("menu:watchlist"),
        )
    await cb.answer()


@router.message(WatchlistSG.add_price)
async def msg_price(message: Message, state: FSMContext) -> None:
    try:
        price = parse_ton_amount(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    await state.update_data(price=price)
    await state.set_state(WatchlistSG.add_direction)
    kb = InlineKeyboardBuilder()
    kb.button(text="📉 ≤ (упадёт ниже)", callback_data="wl:dir:below")
    kb.button(text="📈 ≥ (вырастет выше)", callback_data="wl:dir:above")
    kb.button(text="↩️ Назад", callback_data="menu:watchlist")
    kb.adjust(1)
    await message.answer(
        f"Целевая цена: <b>{price} TON</b>\n\nКогда срабатывать?",
        parse_mode="HTML",
        reply_markup=kb.as_markup(),
    )


@router.callback_query(F.data.startswith("wl:dir:"))
async def cb_dir(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    direction = (cb.data or "").rsplit(":", 1)[-1]
    data = await state.get_data()
    coll = data.get("collection")
    price = data.get("price")
    if not coll or price is None:
        await cb.answer("Нет данных", show_alert=True)
        return
    async with db.session() as sess:
        await WatchlistRepository(sess).add(
            user_id=user.id,
            collection=str(coll),
            target_price=float(price),
            direction=direction,
        )
    await cb.answer("Алерт добавлен")
    await cb_open(cb, state, db, user)


@router.callback_query(F.data.startswith("wl:open:"))
async def cb_open_item(cb: CallbackQuery, db: Database, user) -> None:
    item_id = int((cb.data or "").rsplit(":", 1)[-1])
    async with db.session() as sess:
        item = await WatchlistRepository(sess).get(item_id)
    if not item or item.user_id != user.id:
        await cb.answer("Не найдено", show_alert=True)
        return
    arrow = "≤" if item.direction == "below" else "≥"
    text = (
        f"🔔 <b>Алерт</b>\n\n"
        f"📦 Коллекция: <code>{item.collection}</code>\n"
        f"🎯 Триггер: floor {arrow} {fmt_ton(item.target_price)}\n"
        f"Активен: {'да' if item.is_active else 'нет'}\n"
        f"Создан: {item.created_at:%Y-%m-%d %H:%M}"
        + (f"\nПоследний триггер: {item.last_triggered:%Y-%m-%d %H:%M}" if item.last_triggered else "")
    )
    if cb.message is not None:
        await cb.message.edit_text(
            text, parse_mode="HTML", reply_markup=_detail_kb(item.id, item.is_active).as_markup()
        )
    await cb.answer()


@router.callback_query(F.data.startswith("wl:toggle:"))
async def cb_toggle(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    item_id = int((cb.data or "").rsplit(":", 1)[-1])
    async with db.session() as sess:
        await WatchlistRepository(sess).toggle(item_id)
    await cb.answer("Состояние изменено")
    await cb_open(cb, state, db, user)


@router.callback_query(F.data.startswith("wl:delete:"))
async def cb_delete(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    item_id = int((cb.data or "").rsplit(":", 1)[-1])
    async with db.session() as sess:
        await WatchlistRepository(sess).remove(item_id)
    await cb.answer("Удалено")
    await cb_open(cb, state, db, user)
