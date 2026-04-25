"""/start, main menu, dry-run / auto-trading toggles."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.common import main_menu_kb
from bot.states import MainMenuSG
from db.database import Database
from db.repositories import TradeRepository, UserRepository
from utils.formatters import fmt_main_menu_header

router = Router(name="main")


async def _render_menu(target: Message | CallbackQuery, db: Database, engine, user) -> None:
    async with db.session() as sess:
        stats = await TradeRepository(sess).daily_stats(user.id)
    text = fmt_main_menu_header({
        "balance": engine.market.balance_ton,
        "dry_run": user.dry_run,
        "auto": user.auto_trading,
        "daily_profit": stats["net"],
    })
    kb = main_menu_kb(dry_run=user.dry_run, auto=user.auto_trading)
    if isinstance(target, CallbackQuery) and target.message is not None:
        await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    elif isinstance(target, Message):
        await target.answer(text, reply_markup=kb, parse_mode="HTML")


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, db: Database, engine, user
) -> None:
    await state.set_state(MainMenuSG.main)
    try:
        await engine.balance.refresh()
    except Exception:
        pass
    await _render_menu(message, db, engine, user)


@router.callback_query(F.data == "menu:main")
async def cb_main(
    cb: CallbackQuery, state: FSMContext, db: Database, engine, user
) -> None:
    await state.set_state(MainMenuSG.main)
    await _render_menu(cb, db, engine, user)


@router.callback_query(F.data == "dry_run:toggle")
async def cb_toggle_dry(
    cb: CallbackQuery, state: FSMContext, db: Database, engine, user
) -> None:
    new_value = not user.dry_run
    async with db.session() as sess:
        await UserRepository(sess).update_settings(user.id, dry_run=new_value)
    user.dry_run = new_value
    await cb.answer("DRY-RUN включён" if new_value else "DRY-RUN выключен")
    await _render_menu(cb, db, engine, user)


@router.callback_query(F.data == "auto:toggle")
async def cb_toggle_auto(
    cb: CallbackQuery, state: FSMContext, db: Database, engine, user
) -> None:
    new_value = not user.auto_trading
    async with db.session() as sess:
        await UserRepository(sess).update_settings(user.id, auto_trading=new_value)
    user.auto_trading = new_value
    await cb.answer("Авто-торговля ВКЛ" if new_value else "Авто-торговля ВЫКЛ")
    await _render_menu(cb, db, engine, user)
