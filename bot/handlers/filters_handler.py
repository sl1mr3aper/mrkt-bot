"""Search filters editor with multi-select for attributes."""

from __future__ import annotations

import json
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from bot.keyboards.common import cancel_kb
from bot.states import FiltersSG
from db.database import Database
from db.models import UserFilter
from utils.formatters import fmt_rarity, fmt_ton
from utils.validators import parse_int, parse_ton_amount

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
    kb.button(text="🔎 Найти сейчас", callback_data="filter:run")
    kb.button(text="🏠 Главное меню", callback_data="menu:main")
    kb.adjust(2, 2, 2, 2, 1, 1, 1)
    return kb


async def _load_filter(db: Database, user_id: int) -> UserFilter | None:
    async with db.session() as sess:
        result = await sess.execute(
            select(UserFilter).where(UserFilter.user_id == user_id).limit(1)
        )
        return result.scalar_one_or_none()


async def _load_or_create_filter(db: Database, user_id: int) -> UserFilter:
    f = await _load_filter(db, user_id)
    if f is not None:
        return f
    async with db.session() as sess:
        f = UserFilter(user_id=user_id)
        sess.add(f)
        await sess.flush()
        await sess.refresh(f)
    return f


async def _save_filter(db: Database, f: UserFilter) -> None:
    async with db.session() as sess:
        await sess.merge(f)


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


# ─── multi-select primitives ───────────────────────────────────────


def _multi_select_kb(
    options: list[str],
    selected: list[str],
    *,
    prefix: str,
    page: int = 0,
    per_page: int = 12,
) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    start = page * per_page
    chunk = options[start : start + per_page]
    for opt in chunk:
        mark = "✅ " if opt in selected else "⬜ "
        kb.button(text=f"{mark}{opt}", callback_data=f"{prefix}:t:{opt}")
    kb.adjust(2)
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text="◀️", callback_data=f"{prefix}:p:{page - 1}")
    if start + per_page < len(options):
        nav.button(text="▶️", callback_data=f"{prefix}:p:{page + 1}")
    nav.button(text="🧹 Очистить", callback_data=f"{prefix}:clear")
    nav.button(text="↩️ Назад", callback_data="menu:search")
    nav.adjust(4)
    kb.attach(nav)
    return kb


_FIELD_BY_PREFIX: dict[str, tuple[str, str]] = {
    "filter:colsel": ("collection_names", "📦 Выберите коллекции"),
    "filter:modsel": ("model_names", "🎨 Выберите модели"),
    "filter:bsel": ("backdrop_names", "🖼 Выберите backdrops"),
    "filter:ssel": ("symbol_names", "💎 Выберите symbols"),
}


async def _options_for(prefix: str, engine, f: UserFilter) -> list[str]:
    if prefix == "filter:colsel":
        items = await engine.client.list_collections()
        return sorted({c.get("name") for c in items if c.get("name")})
    if prefix == "filter:modsel":
        coll = json.loads(f.collection_names or "[]") if f else []
        return await engine.client.list_models(coll or None)
    if prefix == "filter:bsel":
        return await engine.client.list_backdrops()
    if prefix == "filter:ssel":
        return await engine.client.list_symbols()
    return []


async def _render_select(
    cb: CallbackQuery,
    db: Database,
    engine,
    user,
    prefix: str,
    page: int = 0,
) -> None:
    field, title = _FIELD_BY_PREFIX[prefix]
    f = await _load_or_create_filter(db, user.id)
    options = await _options_for(prefix, engine, f)
    selected = json.loads(getattr(f, field) or "[]")
    kb = _multi_select_kb(options, selected, prefix=prefix, page=page)
    head = f"{title}\n\nВыбрано: <code>{', '.join(selected) or '—'}</code>"
    if cb.message is not None:
        await cb.message.edit_text(head, parse_mode="HTML", reply_markup=kb.as_markup())


# ─── main filters menu ────────────────────────────────────────────


@router.callback_query(F.data == "menu:search")
async def cb_open_filters(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    await state.set_state(FiltersSG.menu)
    f = await _load_or_create_filter(db, user.id)
    if cb.message is not None:
        await cb.message.edit_text(
            _summary(f), parse_mode="HTML", reply_markup=_filters_kb().as_markup()
        )
    await cb.answer()


@router.callback_query(F.data == "filter:reset")
async def cb_reset(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    f = await _load_or_create_filter(db, user.id)
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


# ─── attribute select handlers ────────────────────────────────────


@router.callback_query(F.data == "filter:collections")
async def cb_collections(cb: CallbackQuery, db: Database, engine, user) -> None:
    await _render_select(cb, db, engine, user, "filter:colsel")
    await cb.answer()


@router.callback_query(F.data == "filter:models")
async def cb_models(cb: CallbackQuery, db: Database, engine, user) -> None:
    await _render_select(cb, db, engine, user, "filter:modsel")
    await cb.answer()


@router.callback_query(F.data == "filter:backdrops")
async def cb_backdrops(cb: CallbackQuery, db: Database, engine, user) -> None:
    await _render_select(cb, db, engine, user, "filter:bsel")
    await cb.answer()


@router.callback_query(F.data == "filter:symbols")
async def cb_symbols(cb: CallbackQuery, db: Database, engine, user) -> None:
    await _render_select(cb, db, engine, user, "filter:ssel")
    await cb.answer()


@router.callback_query(F.data.regexp(r"^filter:(colsel|modsel|bsel|ssel):t:"))
async def cb_toggle_attr(cb: CallbackQuery, db: Database, engine, user) -> None:
    if cb.data is None:
        await cb.answer()
        return
    parts = cb.data.split(":", 3)  # ["filter", "colsel", "t", "<value>"]
    prefix = f"{parts[0]}:{parts[1]}"
    value = parts[3]
    field, _title = _FIELD_BY_PREFIX[prefix]
    f = await _load_or_create_filter(db, user.id)
    selected: list[str] = json.loads(getattr(f, field) or "[]")
    if value in selected:
        selected.remove(value)
    else:
        selected.append(value)
    setattr(f, field, json.dumps(selected, ensure_ascii=False))
    await _save_filter(db, f)
    await _render_select(cb, db, engine, user, prefix)
    await cb.answer(f"{'+' if value in selected else '−'} {value}")


@router.callback_query(F.data.regexp(r"^filter:(colsel|modsel|bsel|ssel):p:\d+$"))
async def cb_page_attr(cb: CallbackQuery, db: Database, engine, user) -> None:
    if cb.data is None:
        await cb.answer()
        return
    parts = cb.data.split(":")
    prefix = f"filter:{parts[1]}"
    page = int(parts[3])
    await _render_select(cb, db, engine, user, prefix, page=page)
    await cb.answer()


@router.callback_query(F.data.regexp(r"^filter:(colsel|modsel|bsel|ssel):clear$"))
async def cb_clear_attr(cb: CallbackQuery, db: Database, engine, user) -> None:
    if cb.data is None:
        await cb.answer()
        return
    prefix = f"filter:{cb.data.split(':')[1]}"
    field, _ = _FIELD_BY_PREFIX[prefix]
    f = await _load_or_create_filter(db, user.id)
    setattr(f, field, "[]")
    await _save_filter(db, f)
    await _render_select(cb, db, engine, user, prefix)
    await cb.answer("Очищено")


# ─── ordering ─────────────────────────────────────────────────────


def _ordering_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 По цене ↑", callback_data="filter:ord:Price:asc")
    kb.button(text="💰 По цене ↓", callback_data="filter:ord:Price:desc")
    kb.button(text="⭐ По редкости ↑", callback_data="filter:ord:Rarity:asc")
    kb.button(text="⭐ По редкости ↓", callback_data="filter:ord:Rarity:desc")
    kb.button(text="🔢 По номеру ↑", callback_data="filter:ord:Number:asc")
    kb.button(text="🔢 По номеру ↓", callback_data="filter:ord:Number:desc")
    kb.button(text="↩️ Назад", callback_data="menu:search")
    kb.adjust(2, 2, 2, 1)
    return kb


@router.callback_query(F.data == "filter:ordering")
async def cb_ordering(cb: CallbackQuery) -> None:
    if cb.message is not None:
        await cb.message.edit_text("⏬ Выберите сортировку:", reply_markup=_ordering_kb().as_markup())
    await cb.answer()


@router.callback_query(F.data.regexp(r"^filter:ord:(Price|Rarity|Number):(asc|desc)$"))
async def cb_set_ordering(
    cb: CallbackQuery, state: FSMContext, db: Database, user
) -> None:
    if cb.data is None:
        await cb.answer()
        return
    _, _, ordering, direction = cb.data.split(":")
    f = await _load_or_create_filter(db, user.id)
    f.ordering = ordering
    f.low_to_high = direction == "asc"
    await _save_filter(db, f)
    await cb.answer(f"✅ {ordering} {direction}")
    await cb_open_filters(cb, state, db, user)


# ─── price / rarity / number scalar handlers ──────────────────────


@router.callback_query(F.data.in_({"filter:price_min", "filter:price_max"}))
async def cb_price(cb: CallbackQuery, state: FSMContext) -> None:
    if cb.data == "filter:price_min":
        await state.set_state(FiltersSG.price_min)
        prompt = "Введите минимальную цену в TON (например <code>0.5</code>):"
    else:
        await state.set_state(FiltersSG.price_max)
        prompt = "Введите максимальную цену в TON (например <code>10</code>):"
    if cb.message is not None:
        await cb.message.edit_text(
            prompt, parse_mode="HTML", reply_markup=cancel_kb("menu:search")
        )
    await cb.answer()


@router.message(FiltersSG.price_min)
async def msg_price_min(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_ton_amount(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    f = await _load_or_create_filter(db, user.id)
    f.min_price = value
    await _save_filter(db, f)
    await message.answer(
        f"✅ Минимальная цена = {value} TON\n\n" + _summary(f),
        parse_mode="HTML",
        reply_markup=_filters_kb().as_markup(),
    )
    await state.set_state(FiltersSG.menu)


@router.message(FiltersSG.price_max)
async def msg_price_max(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_ton_amount(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    f = await _load_or_create_filter(db, user.id)
    f.max_price = value
    await _save_filter(db, f)
    await message.answer(
        f"✅ Максимальная цена = {value} TON\n\n" + _summary(f),
        parse_mode="HTML",
        reply_markup=_filters_kb().as_markup(),
    )
    await state.set_state(FiltersSG.menu)


@router.callback_query(F.data == "filter:rarity")
async def cb_rarity(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FiltersSG.rarity)
    if cb.message is not None:
        await cb.message.edit_text(
            "Введите минимальный rarity score (0..10), например <code>7</code>:",
            parse_mode="HTML",
            reply_markup=cancel_kb("menu:search"),
        )
    await cb.answer()


@router.message(FiltersSG.rarity)
async def msg_rarity(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_ton_amount(message.text or "", min_value=0.0, max_value=10.0)
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    f = await _load_or_create_filter(db, user.id)
    f.rarity_min = value
    await _save_filter(db, f)
    await message.answer(
        f"✅ Rarity ≥ {value}\n\n" + _summary(f),
        parse_mode="HTML",
        reply_markup=_filters_kb().as_markup(),
    )
    await state.set_state(FiltersSG.menu)


@router.callback_query(F.data == "filter:number")
async def cb_number(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(FiltersSG.number)
    if cb.message is not None:
        await cb.message.edit_text(
            "Введите номер (целое число) или <code>0</code> чтобы сбросить:",
            parse_mode="HTML",
            reply_markup=cancel_kb("menu:search"),
        )
    await cb.answer()


@router.message(FiltersSG.number)
async def msg_number(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_int(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    f = await _load_or_create_filter(db, user.id)
    f.number_filter = value if value > 0 else None
    await _save_filter(db, f)
    head = (
        f"✅ Номер = {value}" if value > 0 else "✅ Фильтр номера сброшен"
    )
    await message.answer(
        head + "\n\n" + _summary(f),
        parse_mode="HTML",
        reply_markup=_filters_kb().as_markup(),
    )
    await state.set_state(FiltersSG.menu)


# ─── run search ───────────────────────────────────────────────────


def _filter_to_search_kwargs(f: UserFilter) -> dict[str, Any]:
    try:
        coll = json.loads(f.collection_names or "[]")
        models = json.loads(f.model_names or "[]")
        backdrops = json.loads(f.backdrop_names or "[]")
        symbols = json.loads(f.symbol_names or "[]")
    except json.JSONDecodeError:
        coll = models = backdrops = symbols = []
    return {
        "collection_names": coll or None,
        "model_names": models or None,
        "backdrop_names": backdrops or None,
        "symbol_names": symbols or None,
        "ordering": f.ordering or "Price",
        "low_to_high": bool(f.low_to_high),
        "min_price_ton": f.min_price,
        "max_price_ton": f.max_price,
        "number": f.number_filter,
        "count": 15,
    }


def _results_kb(cursor: str, total: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    if cursor:
        kb.button(text="▶️ Ещё", callback_data=f"search:next:{cursor}")
    kb.button(text="↩️ К фильтрам", callback_data="menu:search")
    kb.button(text="🏠 Главное меню", callback_data="menu:main")
    kb.adjust(1)
    return kb


def _format_results(items: list[dict[str, Any]], total: int, rarity_min: float | None) -> str:
    if not items:
        return "🔭 Ничего не найдено по текущим фильтрам."
    lines = [f"🔍 <b>Найдено: {total}</b> (показ {len(items)})", ""]
    for g in items:
        score = (g.get("modelRarity") or 50.0)
        if rarity_min is not None and score and score / 10.0 < rarity_min:
            continue  # client-side rarity filter
        title = g.get("title") or g.get("name") or g.get("id") or "?"
        coll = g.get("collection_title") or g.get("collection") or ""
        price = g.get("price")
        rar = fmt_rarity(score / 10.0 if score else None)
        lines.append(
            f"• <b>{title[:32]}</b> — {fmt_ton(price)}  ⭐ {rar}\n"
            f"   <i>{coll}</i>  ⌗{g.get('number') or '—'}"
        )
    return "\n".join(lines)


@router.callback_query(F.data == "filter:run")
async def cb_run_search(cb: CallbackQuery, db: Database, engine, user) -> None:
    f = await _load_or_create_filter(db, user.id)
    kwargs = _filter_to_search_kwargs(f)
    try:
        page = await engine.client.search_gifts(**kwargs)
    except Exception as exc:
        if cb.message is not None:
            await cb.message.edit_text(f"❌ Ошибка поиска: {exc}")
        await cb.answer()
        return
    text = _format_results(page["items"], page["total"], f.rarity_min)
    if cb.message is not None:
        await cb.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=_results_kb(page["cursor"], page["total"]).as_markup(),
        )
    await cb.answer()


@router.callback_query(F.data.regexp(r"^search:next:"))
async def cb_search_next(cb: CallbackQuery, db: Database, engine, user) -> None:
    if cb.data is None:
        await cb.answer()
        return
    cursor = cb.data.split(":", 2)[2]
    f = await _load_or_create_filter(db, user.id)
    kwargs = _filter_to_search_kwargs(f)
    kwargs["cursor"] = cursor
    try:
        page = await engine.client.search_gifts(**kwargs)
    except Exception as exc:
        if cb.message is not None:
            await cb.message.edit_text(f"❌ Ошибка поиска: {exc}")
        await cb.answer()
        return
    text = _format_results(page["items"], page["total"], f.rarity_min)
    if cb.message is not None:
        await cb.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=_results_kb(page["cursor"], page["total"]).as_markup(),
        )
    await cb.answer()
