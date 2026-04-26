"""User settings (stop-loss, max buy, min profit, large deal, proxy)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.common import cancel_kb, settings_kb
from bot.states import SettingsSG
from db.database import Database
from db.repositories import UserRepository
from utils.formatters import fmt_pct, fmt_ton
from utils.validators import parse_pct, parse_ton_amount

router = Router(name="settings")


def _summary(user) -> str:
    return (
        "⚙️ <b>Настройки</b>\n\n"
        f"🛡 Стоп-лосс: {fmt_pct(user.stop_loss_pct, sign=False)}\n"
        f"💰 Макс. покупка: {fmt_ton(user.max_buy_ton)}\n"
        f"📈 Мин. прибыль: {fmt_ton(user.min_profit_ton)}\n"
        f"🎯 Крупная сделка: ≥ {fmt_ton(user.large_deal_ton)}\n"
        f"🌐 Прокси: <code>{user.proxy_url or 'не задан'}</code>\n"
        f"🧪 DRY-RUN: {'ON' if user.dry_run else 'OFF'}\n"
    )


@router.callback_query(F.data == "menu:settings")
async def cb_open(cb: CallbackQuery, state: FSMContext, user) -> None:
    await state.set_state(SettingsSG.main)
    if cb.message is not None:
        await cb.message.edit_text(
            _summary(user), parse_mode="HTML", reply_markup=settings_kb()
        )
    await cb.answer()


@router.callback_query(F.data == "set:stop_loss")
async def cb_stop(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsSG.stop_loss_pct)
    if cb.message is not None:
        await cb.message.edit_text(
            "Введите стоп-лосс (%): например <code>15</code>",
            parse_mode="HTML",
            reply_markup=cancel_kb("menu:settings"),
        )
    await cb.answer()


@router.message(SettingsSG.stop_loss_pct)
async def msg_stop(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_pct(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    async with db.session() as sess:
        await UserRepository(sess).update_settings(user.id, stop_loss_pct=value)
    user.stop_loss_pct = value
    await message.answer(
        f"✅ Стоп-лосс = {value}%\n\n" + _summary(user),
        parse_mode="HTML",
        reply_markup=settings_kb(),
    )
    await state.set_state(SettingsSG.main)


@router.callback_query(F.data == "set:max_buy")
async def cb_max(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsSG.max_buy_ton)
    if cb.message is not None:
        await cb.message.edit_text(
            "Максимальная стоимость одной покупки (TON):",
            reply_markup=cancel_kb("menu:settings"),
        )
    await cb.answer()


@router.message(SettingsSG.max_buy_ton)
async def msg_max(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_ton_amount(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    async with db.session() as sess:
        await UserRepository(sess).update_settings(user.id, max_buy_ton=value)
    user.max_buy_ton = value
    await message.answer(
        f"✅ Макс. покупка = {value} TON\n\n" + _summary(user),
        parse_mode="HTML",
        reply_markup=settings_kb(),
    )
    await state.set_state(SettingsSG.main)


@router.callback_query(F.data == "set:min_profit")
async def cb_min_profit(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsSG.min_profit_ton)
    if cb.message is not None:
        await cb.message.edit_text(
            "Минимальная прибыль за сделку (TON):",
            reply_markup=cancel_kb("menu:settings"),
        )
    await cb.answer()


@router.message(SettingsSG.min_profit_ton)
async def msg_min_profit(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_ton_amount(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    async with db.session() as sess:
        await UserRepository(sess).update_settings(user.id, min_profit_ton=value)
    user.min_profit_ton = value
    await message.answer(
        f"✅ Мин. прибыль = {value} TON\n\n" + _summary(user),
        parse_mode="HTML",
        reply_markup=settings_kb(),
    )
    await state.set_state(SettingsSG.main)


@router.callback_query(F.data == "set:large_deal")
async def cb_large(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsSG.large_deal_confirm)
    if cb.message is not None:
        await cb.message.edit_text(
            "Порог 'крупной сделки' (TON), требующий подтверждения:",
            reply_markup=cancel_kb("menu:settings"),
        )
    await cb.answer()


@router.message(SettingsSG.large_deal_confirm)
async def msg_large(message: Message, state: FSMContext, db: Database, user) -> None:
    try:
        value = parse_ton_amount(message.text or "")
    except Exception as exc:
        await message.answer(f"❌ {exc}")
        return
    async with db.session() as sess:
        await UserRepository(sess).update_settings(user.id, large_deal_ton=value)
    user.large_deal_ton = value
    await message.answer(
        f"✅ Крупная сделка ≥ {value} TON\n\n" + _summary(user),
        parse_mode="HTML",
        reply_markup=settings_kb(),
    )
    await state.set_state(SettingsSG.main)


@router.callback_query(F.data == "set:proxy")
async def cb_proxy(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsSG.proxy_input)
    if cb.message is not None:
        await cb.message.edit_text(
            "Введите proxy URL вида <code>socks5://user:pass@host:port</code> "
            "или <code>none</code> чтобы удалить.",
            parse_mode="HTML",
            reply_markup=cancel_kb("menu:settings"),
        )
    await cb.answer()


@router.message(SettingsSG.proxy_input)
async def msg_proxy(message: Message, state: FSMContext, db: Database, user) -> None:
    text = (message.text or "").strip()
    proxy = None if text.lower() in {"none", "off", "-"} else text
    async with db.session() as sess:
        await UserRepository(sess).update_settings(user.id, proxy_url=proxy)
    user.proxy_url = proxy
    await message.answer(
        ("✅ Прокси сохранён" if proxy else "✅ Прокси удалён") + "\n\n" + _summary(user),
        parse_mode="HTML",
        reply_markup=settings_kb(),
    )
    await state.set_state(SettingsSG.main)


@router.callback_query(F.data == "set:dry_run")
async def cb_dry(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    new_value = not user.dry_run
    async with db.session() as sess:
        await UserRepository(sess).update_settings(user.id, dry_run=new_value)
    user.dry_run = new_value
    await cb.answer(f"DRY-RUN {'ON' if new_value else 'OFF'}")
    await cb_open(cb, state, user)


@router.callback_query(F.data == "set:notifications")
async def cb_notif(cb: CallbackQuery) -> None:
    await cb.answer("Используйте /start → главное меню для управления уведомлениями")
