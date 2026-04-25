"""Strategy CRUD UI."""

from __future__ import annotations

import json

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.common import strategy_list_kb
from bot.states import StrategySG
from db.database import Database
from db.repositories import StrategyRepository
from strategies import STRATEGY_REGISTRY

router = Router(name="strategies")


def _types_kb():
    kb = InlineKeyboardBuilder()
    for type_id, cls in STRATEGY_REGISTRY.items():
        kb.button(text=cls.display_name, callback_data=f"strategy:create:{type_id}")
    kb.button(text="↩️ Назад", callback_data="menu:strategies")
    kb.adjust(1)
    return kb.as_markup()


def _detail_kb(sid: int, active: bool):
    kb = InlineKeyboardBuilder()
    kb.button(
        text=("⏸ Остановить" if active else "▶️ Запустить"),
        callback_data=f"strategy:toggle:{sid}",
    )
    kb.button(text="🗑 Удалить", callback_data=f"strategy:delete:{sid}")
    kb.button(text="↩️ Назад", callback_data="menu:strategies")
    kb.adjust(2, 1)
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
    text = (
        f"🤖 <b>{strat.name}</b> (<code>{strat.type}</code>)\n"
        f"Активна: {'да' if strat.is_active else 'нет'}\n\n"
        "Параметры:\n"
        f"<pre>{json.dumps(params, indent=2, ensure_ascii=False)}</pre>"
    )
    if cb.message is not None:
        await cb.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=_detail_kb(strat.id, strat.is_active),
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
