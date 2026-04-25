"""/start, main menu, dry-run / auto-trading toggles."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.common import back_button, main_menu_kb
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


_HELP_TEXT = (
    "❓ <b>Справка по боту</b>\n\n"
    "<b>🔍 Поиск/Фильтры</b> — выбираешь коллекции, модели, фоны, символы; "
    "ставишь min/max цену и rarity; кнопка «Найти сейчас» делает поиск.\n\n"
    "<b>🤖 Стратегии</b> — 10 типов автоматической торговли. "
    "Жми «ℹ️ Описание» в карточке стратегии — там подробное объяснение, "
    "риск-профиль, пример работы и параметры.\n\n"
    "<b>📈 Аналитика</b> — топ-прибыли/убытки, ликвидность коллекций, "
    "горячие/холодные коллекции, скоркарта, P&L по периодам и графики.\n\n"
    "<b>🔔 Watchlist</b> — алерты на пересечение floor-цены коллекцией.\n\n"
    "<b>🧪 DRY-RUN</b> — режим без реальных сделок (по умолчанию ON). "
    "Все «покупки» и «продажи» только логируются.\n\n"
    "<b>⚠️ Реальная торговля</b>\n"
    "Бот может торговать на маркете <b>tgmrkt.io</b> только при наличии "
    "<code>MRKT_API_ID</code>/<code>MRKT_API_HASH</code> от my.telegram.org. "
    "Без них работает в DRY-RUN с локально сгенерированными данными "
    "(56 коллекций, ~670 листингов)."
)


@router.callback_query(F.data == "menu:help")
async def cb_help(cb: CallbackQuery) -> None:
    if cb.message is not None:
        await cb.message.edit_text(
            _HELP_TEXT, parse_mode="HTML", reply_markup=back_button("menu:main")
        )
    await cb.answer()
