"""Strategy CRUD UI."""

from __future__ import annotations

import json

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.common import back_button, strategy_detail_kb, strategy_list_kb
from bot.states import StrategySG
from db.database import Database
from db.repositories import StrategyRepository
from strategies import STRATEGY_REGISTRY
from strategies.info import get_info, list_all, render_card

router = Router(name="strategies")


def _types_kb():
    kb = InlineKeyboardBuilder()
    for type_id, cls in STRATEGY_REGISTRY.items():
        kb.button(text=cls.display_name, callback_data=f"strategy:create:{type_id}")
    kb.button(text="ℹ️ Справка по типам", callback_data="strategy:catalog")
    kb.button(text="↩️ Назад", callback_data="menu:strategies")
    kb.adjust(1)
    return kb.as_markup()


def _catalog_kb():
    kb = InlineKeyboardBuilder()
    for info in list_all():
        kb.button(text=f"ℹ️ {info.display_name}", callback_data=f"strategy:info:{info.type_id}")
    kb.button(text="↩️ Назад", callback_data="strategy:new")
    kb.adjust(2)
    return kb.as_markup()


@router.callback_query(F.data == "menu:strategies")
async def cb_strategies(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    await state.set_state(StrategySG.list)
    async with db.session() as sess:
        strategies = await StrategyRepository(sess).list_by_user(user.id)
    items = [(s.id, f"{s.name} ({s.type})", s.is_active) for s in strategies]
    if cb.message is not None:
        await cb.message.edit_text(
            "🤖 <b>Стратегии</b>\n\nВыбери для управления или создай новую.",
            parse_mode="HTML",
            reply_markup=strategy_list_kb(items),
        )
    await cb.answer()


@router.callback_query(F.data == "strategy:new")
async def cb_new(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(StrategySG.create_choose)
    if cb.message is not None:
        await cb.message.edit_text(
            "Выберите тип стратегии:",
            reply_markup=_types_kb(),
        )
    await cb.answer()


@router.callback_query(F.data.startswith("strategy:create:"))
async def cb_create(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    type_id = (cb.data or "").rsplit(":", 1)[-1]
    cls = STRATEGY_REGISTRY.get(type_id)
    if not cls:
        await cb.answer("Неизвестная стратегия", show_alert=True)
        return
    async with db.session() as sess:
        strat = await StrategyRepository(sess).create(
            user_id=user.id,
            name=cls.display_name,
            type_=type_id,
            params=dict(cls.default_params),
            is_active=False,
        )
    await cb.answer(f"Создана стратегия #{strat.id}")
    await cb_strategies(cb, state, db, user)


@router.callback_query(F.data.startswith("strategy:open:"))
async def cb_open(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    sid = int((cb.data or "").rsplit(":", 1)[-1])
    async with db.session() as sess:
        strat = await StrategyRepository(sess).get(sid)
    if not strat or strat.user_id != user.id:
        await cb.answer("Не найдена", show_alert=True)
        return
    try:
        params = json.loads(strat.params or "{}")
    except json.JSONDecodeError:
        params = {}
    info = get_info(strat.type)
    short = (info.short if info else "")
    text = (
        f"🤖 <b>{strat.name}</b> (<code>{strat.type}</code>)\n"
        f"Активна: {'✅ да' if strat.is_active else '⛔ нет'}\n"
        + (f"\n<i>{short}</i>\n" if short else "")
        + "\n📝 <b>Параметры:</b>\n"
        f"<pre>{json.dumps(params, indent=2, ensure_ascii=False)}</pre>"
    )
    if cb.message is not None:
        await cb.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=strategy_detail_kb(
                strat.id, active=strat.is_active, type_id=strat.type
            ),
        )
    await cb.answer()


@router.callback_query(F.data == "strategy:catalog")
async def cb_catalog(cb: CallbackQuery) -> None:
    if cb.message is not None:
        await cb.message.edit_text(
            "📚 <b>Каталог стратегий</b>\n\nНажми, чтобы прочитать описание.",
            parse_mode="HTML",
            reply_markup=_catalog_kb(),
        )
    await cb.answer()


@router.callback_query(F.data.startswith("strategy:info:"))
async def cb_info(cb: CallbackQuery) -> None:
    type_id = (cb.data or "").rsplit(":", 1)[-1]
    info = get_info(type_id)
    if info is None:
        await cb.answer("Нет описания", show_alert=True)
        return
    if cb.message is not None:
        await cb.message.edit_text(
            render_card(info),
            parse_mode="HTML",
            reply_markup=back_button("strategy:catalog"),
        )
    await cb.answer()


@router.callback_query(F.data.startswith("strategy:params:"))
async def cb_params(cb: CallbackQuery, db: Database, user) -> None:
    sid = int((cb.data or "").rsplit(":", 1)[-1])
    async with db.session() as sess:
        strat = await StrategyRepository(sess).get(sid)
    if not strat or strat.user_id != user.id:
        await cb.answer("Не найдена", show_alert=True)
        return
    info = get_info(strat.type)
    try:
        params = json.loads(strat.params or "{}")
    except json.JSONDecodeError:
        params = {}
    rows = ["📝 <b>Параметры стратегии</b>", ""]
    if info and info.params:
        for key, default, doc in info.params:
            cur = params.get(key, "—")
            rows.append(f"• <code>{key}</code> = <b>{cur}</b> (default: {default})")
            if doc:
                rows.append(f"  <i>{doc}</i>")
    else:
        rows.append("<i>Описание параметров недоступно для этого типа.</i>")
    if cb.message is not None:
        await cb.message.edit_text(
            "\n".join(rows),
            parse_mode="HTML",
            reply_markup=back_button(f"strategy:open:{sid}"),
        )
    await cb.answer()


@router.callback_query(F.data.startswith("strategy:toggle:"))
async def cb_toggle(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    sid = int((cb.data or "").rsplit(":", 1)[-1])
    async with db.session() as sess:
        repo = StrategyRepository(sess)
        strat = await repo.get(sid)
        if not strat or strat.user_id != user.id:
            await cb.answer("Не найдена", show_alert=True)
            return
        await repo.set_active(sid, not strat.is_active)
    await cb.answer("Обновлено")
    await cb_open(cb, state, db, user)


@router.callback_query(F.data.startswith("strategy:delete:"))
async def cb_delete(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    sid = int((cb.data or "").rsplit(":", 1)[-1])
    async with db.session() as sess:
        repo = StrategyRepository(sess)
        strat = await repo.get(sid)
        if strat and strat.user_id == user.id:
            await repo.delete(sid)
    await cb.answer("Удалена")
    await cb_strategies(cb, state, db, user)


@router.message(StrategySG.custom_name)
async def msg_custom_name(message: Message, state: FSMContext) -> None:
    await state.update_data(custom_name=(message.text or "Custom"))
    await message.answer("Имя сохранено. Перейдите в стратегии.")
    await state.set_state(StrategySG.list)


@router.callback_query(F.data.startswith("strategy:backtest:"))
async def cb_backtest(cb: CallbackQuery, db: Database, engine, user) -> None:
    """Run a quick backtest of the strategy on the latest market snapshot."""
    sid = int((cb.data or "").rsplit(":", 1)[-1])
    async with db.session() as sess:
        strat = await StrategyRepository(sess).get(sid)
    if not strat or strat.user_id != user.id:
        await cb.answer("Не найдена", show_alert=True)
        return
    cls = STRATEGY_REGISTRY.get(strat.type)
    if cls is None:
        await cb.answer("Тип стратегии неизвестен", show_alert=True)
        return
    try:
        params = json.loads(strat.params or "{}")
    except json.JSONDecodeError:
        params = {}
    instance = cls(params)

    # Aggregate listings across all collections (cap to 800 to stay snappy).
    listings: list[dict] = []
    for snap in engine.market.collections.values():
        if not snap.listings:
            continue
        listings.extend(list(snap.listings)[:30])
        if len(listings) >= 800:
            break
    if not listings:
        await cb.answer("Нет рыночных данных", show_alert=True)
        return

    from core.backtest_engine import BacktestEngine

    report = BacktestEngine().run(instance, listings)
    text = "🧪 <b>Backtest</b>\n<i>На текущем срезе рынка</i>\n\n" + report.render()
    if report.skipped_reasons:
        text += "\n\n<b>Топ причин пропусков:</b>\n"
        top = sorted(report.skipped_reasons.items(), key=lambda kv: -kv[1])[:5]
        for reason, n in top:
            text += f"• <code>{reason}</code>: {n}\n"
    if cb.message is not None:
        await cb.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=back_button(f"strategy:open:{sid}"),
        )
    await cb.answer()
