"""Search filters editor."""

from __future__ import annotations

import json

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from bot.states import FiltersSG
from db.database import Database
from db.models import UserFilter
from utils.validators import parse_ton_amount

router = Router(name="filters")


def _filters_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Коллекции", callback_data="filter:collections")
    kb.button(text="🎨 Модели", callback_data="filter:models")
    kb.button(text="🖼 Backdrops", callback_data="filter:backdrops")
    kb.button(text="💎 Symbols", callback_data="filter:symbols")
    kb.button(text="💰 Цена min", callback_data="filter:price_min")
    kb.button(text="💰 Цена max", callback_data="filter:price_max")
    kb.button(text="⭐ Rarity ≥", callback_data="filter:rarity")
    kb.button(text="⏬ Сортировка", callback_data="filter:ordering")
    kb.button(text="🔢 Номер", callback_data="filter:number")
    kb.button(text="🧹 Сбросить", callback_data="filter:reset")
    kb.button(text="🏠 Главное меню", callback_data="menu:main")
    kb.adjust(2, 2, 2, 2, 1, 1)
    return kb


async def _load_filter(db: Database, user_id: int) -> UserFilter | None:
    async with db.session() as sess:
        result = await sess.execute(
            select(UserFilter).where(UserFilter.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none()


async def _save_filter(db: Database, f: UserFilter) -> None:
    async with db.session() as sess:
        sess.add(f)


def _summary(f: UserFilter | None) -> str:
    if not f:
        return "Фильтры не настроены."
    try:
        coll = json.loads(f.collection_names or "[]")
        models = json.loads(f.model_names or "[]")
        backdrops = json.loads(f.backdrop_names or "[]")
        symbols = json.loads(f.symbol_names or "[]")
    except json.JSONDecodeError:
        coll = models = backdrops = symbols = []
    return (
        "🎯 <b>Текущие фильтры</b>\n\n"
        f"📦 Коллекции: <code>{', '.join(coll) or 'все'}</code>\n"
        f"🎨 Модели: <code>{', '.join(models) or 'все'}</code>\n"
        f"🖼 Backdrops: <code>{', '.join(backdrops) or 'все'}</code>\n"
        f"💎 Symbols: <code>{', '.join(symbols) or 'все'}</code>\n"
        f"💰 Цена: {f.min_price or '—'}–{f.max_price or '—'} TON\n"
        f"⭐ Rarity ≥ {f.rarity_min or '—'}\n"
        f"🔢 Номер: {f.number_filter or '—'}\n"
        f"⏬ Сортировка: {f.ordering} ({'asc' if f.low_to_high else 'desc'})\n"
    )


@router.callback_query(F.data == "menu:search")
async def cb_open_filters(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    await state.set_state(FiltersSG.menu)
    f = await _load_filter(db, user.id)
    if cb.message is not None:
        await cb.message.edit_text(
            _summary(f), parse_mode="HTML", reply_markup=_filters_kb().as_markup()
        )
    await cb.answer()


@router.callback_query(F.data == "filter:reset")
async def cb_reset(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    f = await _load_filter(db, user.id)
    if f:
        f.collection_names = "[]"
        f.model_names = "[]"
        f.backdrop_names = "[]"
        f.symbol_names = "[]"
        f.min_price = None
        f.max_price = None
        f.rarity_min = None
        f.number_filter = None
        f.ordering = "Price"
        f.low_to_high = True
        await _save_filter(db, f)
    await cb_open_filters(cb, state, db, user)


@router.callback_query(F.data.in_({"filter:price_min", "filter:price_max"}))
async def cb_price(cb: CallbackQuery, state: FSMContext) -> None:
    if cb.data == "filter:price_min":
        await state.set_state(FiltersSG.price_min)
        prompt = "Введите минимальную цену в TON (например 0.5):"
    else:
        await state.set_state(FiltersSG.price_max)
        prompt = "Введите максимальную цену в TON (например 10):"
    if cb.message is not None:
        await cb.message.edit_text(prompt)
    await cb.answer()


@router.message(FiltersSG.price_min)
async def msg_price_min(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_ton_amount(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    f = await _load_filter(db, user.id)
    if f:
        f.min_price = value
        await _save_filter(db, f)
    await message.answer(f"✅ Минимальная цена = {value} TON")
    await state.set_state(FiltersSG.menu)


@router.message(FiltersSG.price_max)
async def msg_price_max(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_ton_amount(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    f = await _load_filter(db, user.id)
    if f:
        f.max_price = value
        await _save_filter(db, f)
    await message.answer(f"✅ Максимальная цена = {value} TON")
    await state.set_state(FiltersSG.menu)


@router.callback_query(F.data == "filter:rarity")
async def cb_rarity(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FiltersSG.rarity)
    if cb.message is not None:
        await cb.message.edit_text("Введите минимальный rarity score (0..10):")
    await cb.answer()


@router.message(FiltersSG.rarity)
async def msg_rarity(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_ton_amount(message.text or "", min_value=0.0, max_value=10.0)
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    f = await _load_filter(db, user.id)
    if f:
        f.rarity_min = value
        await _save_filter(db, f)
    await message.answer(f"✅ Rarity ≥ {value}")
    await state.set_state(FiltersSG.menu)
