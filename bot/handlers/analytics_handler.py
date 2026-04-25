"""Analytics menu, top gainers/losers, charts."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery

from analytics.charts import HAS_MPL, render_floor_chart, render_pnl_chart
from bot.keyboards.common import analytics_menu_kb
from bot.states import AnalyticsSG
from db.database import Database
from db.repositories import PriceRepository, TradeRepository
from utils.formatters import fmt_pct, fmt_ton

router = Router(name="analytics")


@router.callback_query(F.data == "menu:analytics")
async def cb_analytics(cb: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AnalyticsSG.main)
    if cb.message is not None:
        await cb.message.edit_text(
            "📈 <b>Аналитика</b>\n\nВыбери раздел.",
            parse_mode="HTML",
            reply_markup=analytics_menu_kb(),
        )
    await cb.answer()


@router.callback_query(F.data.in_({"analytics:gainers", "analytics:losers"}))
async def cb_top(cb: CallbackQuery, state: FSMContext, db: Database, user) -> None:
    is_gainers = cb.data == "analytics:gainers"
    async with db.session() as sess:
        repo = TradeRepository(sess)
        rows = await (
            repo.top_gainers(user.id, days=7) if is_gainers else repo.top_losers(user.id, days=7)
        )
    if not rows:
        text = "Нет данных за последние 7 дней."
    else:
        lines = [
            "🚀 <b>Топ-прибыль (7д)</b>" if is_gainers else "📉 <b>Топ-убытки (7д)</b>",
            "",
        ]
        for t in rows:
            lines.append(
                f"<code>{(t.gift_name or '')[:20]}</code> "
                f"{fmt_ton(t.net_profit, sign=True)} ({fmt_pct(t.profit_pct)})"
            )
        text = "\n".join(lines)
    if cb.message is not None:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=analytics_menu_kb())
    await cb.answer()


@router.callback_query(F.data == "analytics:liquidity")
async def cb_liquidity(cb: CallbackQuery, state: FSMContext, engine) -> None:
    snaps = engine.market.collections
    if not snaps:
        text = "Нет данных по коллекциям."
    else:
        lines = ["💧 <b>Ликвидность</b>", ""]
        for name, snap in list(snaps.items())[:15]:
            lines.append(
                f"📦 <code>{name[:18]}</code> floor {fmt_ton(snap.floor_price)} "
                f"vol={snap.volume} listings={len(snap.listings)}"
            )
        text = "\n".join(lines)
    if cb.message is not None:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=analytics_menu_kb())
    await cb.answer()


@router.callback_query(F.data == "analytics:chart_pnl")
async def cb_chart_pnl(cb: CallbackQuery, db: Database, user) -> None:
    if not HAS_MPL or cb.message is None:
        await cb.answer("Графики недоступны", show_alert=True)
        return
    async with db.session() as sess:
        trades = await TradeRepository(sess).list_by_user(user.id, limit=100)
    if not trades:
        await cb.answer("Нет сделок для графика", show_alert=True)
        return
    dates = [t.sold_at for t in reversed(trades)]
    profits = [t.net_profit for t in reversed(trades)]
    png = render_pnl_chart("P&L", dates, profits)
    await cb.message.answer_photo(
        BufferedInputFile(png, filename="pnl.png"),
        caption="Cumulative P&L по последним 100 сделкам",
    )
    await cb.answer()


@router.callback_query(F.data == "analytics:chart_floor")
async def cb_chart_floor(cb: CallbackQuery, db: Database, engine) -> None:
    if not HAS_MPL or cb.message is None:
        await cb.answer("Графики недоступны", show_alert=True)
        return
    if not engine.market.collections:
        await cb.answer("Нет коллекций", show_alert=True)
        return
    name = next(iter(engine.market.collections))
    async with db.session() as sess:
        snaps = await PriceRepository(sess).history(name, hours=24 * 7)
    if not snaps:
        await cb.answer("Нет ценовой истории", show_alert=True)
        return
    png = render_floor_chart(
        f"Floor — {name}",
        [s.recorded_at for s in snaps],
        [s.floor_price or 0.0 for s in snaps],
    )
    await cb.message.answer_photo(
        BufferedInputFile(png, filename="floor.png"),
        caption=f"Floor price ({name}) — 7д",
    )
    await cb.answer()
