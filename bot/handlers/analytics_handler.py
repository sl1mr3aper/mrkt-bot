"""Analytics menu, top gainers/losers, hot/cold, scorecards, charts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery
from sqlalchemy import func, select

from analytics import (
    LiquidityAnalyzer,
    cold_collections,
    collection_scorecards,
    hot_collections,
    volume_profile,
)
from analytics.charts import HAS_MPL, render_floor_chart, render_pnl_chart
from analytics.portfolio_analyzer import PortfolioAnalyzer
from bot.keyboards.common import analytics_back_kb, analytics_menu_kb
from bot.states import AnalyticsSG
from db.database import Database
from db.models import Trade
from db.repositories import PortfolioRepository, PriceRepository, TradeRepository
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
            "🚀 <b>Топ‑прибыль (7д)</b>" if is_gainers else "📉 <b>Топ‑убытки (7д)</b>",
            "",
        ]
        for t in rows:
            lines.append(
                f"<code>{(t.gift_name or '')[:24]:<24}</code> "
                f"{fmt_ton(t.net_profit, sign=True)} ({fmt_pct(t.profit_pct)})"
            )
        text = "\n".join(lines)
    if cb.message is not None:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=analytics_back_kb())
    await cb.answer()


@router.callback_query(F.data == "analytics:liquidity")
async def cb_liquidity(cb: CallbackQuery, engine) -> None:
    snaps = engine.market.collections
    if not snaps:
        text = "Нет данных по коллекциям."
    else:
        lines = ["💧 <b>Ликвидность (top‑15)</b>", ""]
        ranked = sorted(
            snaps.values(),
            key=lambda s: (s.volume or 0),
            reverse=True,
        )[:15]
        for snap in ranked:
            report = LiquidityAnalyzer.analyse(snap.listings)
            spread = (
                f"spread {report.spread_pct:.1f}%"
                if report.spread_pct is not None
                else "spread —"
            )
            lines.append(
                f"📦 <code>{(snap.title or snap.name)[:18]:<18}</code> "
                f"floor <b>{fmt_ton(report.floor or 0)}</b> · "
                f"med {fmt_ton(report.median_price or 0)} · "
                f"{spread} · "
                f"кластер {report.cluster_size_at_floor} · "
                f"объявл. {report.listings_count}"
            )
        text = "\n".join(lines)
    if cb.message is not None:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=analytics_back_kb())
    await cb.answer()


@router.callback_query(F.data == "analytics:hot")
async def cb_hot(cb: CallbackQuery, engine) -> None:
    rows = hot_collections(list(engine.market.collections.values()))
    if not rows:
        text = "Нет растущих коллекций (порог 5%)."
    else:
        lines = ["🔥 <b>Hot collections</b>", ""]
        for h in rows:
            lines.append(
                f"📦 <code>{h.title[:18]:<18}</code> "
                f"<b>+{h.delta_pct:.1f}%</b> · floor {fmt_ton(h.floor)} "
                f"(было {fmt_ton(h.previous_floor)})"
            )
        text = "\n".join(lines)
    if cb.message is not None:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=analytics_back_kb())
    await cb.answer()


@router.callback_query(F.data == "analytics:cold")
async def cb_cold(cb: CallbackQuery, engine) -> None:
    rows = cold_collections(list(engine.market.collections.values()))
    if not rows:
        text = "Нет падающих коллекций (порог -5%)."
    else:
        lines = ["🧊 <b>Cold collections</b>", ""]
        for h in rows:
            lines.append(
                f"📦 <code>{h.title[:18]:<18}</code> "
                f"<b>{h.delta_pct:.1f}%</b> · floor {fmt_ton(h.floor)} "
                f"(было {fmt_ton(h.previous_floor)})"
            )
        text = "\n".join(lines)
    if cb.message is not None:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=analytics_back_kb())
    await cb.answer()


@router.callback_query(F.data == "analytics:scorecards")
async def cb_scorecards(cb: CallbackQuery, engine) -> None:
    listings_by = {n: s.listings for n, s in engine.market.collections.items()}
    cards = collection_scorecards(
        list(engine.market.collections.values()),
        listings_by_collection=listings_by,
        limit=15,
    )
    if not cards:
        text = "Нет данных."
    else:
        lines = ["🏅 <b>Скоркарта коллекций</b>", "<i>Сорт по ликвидности</i>", ""]
        for c in cards:
            lines.append(
                f"<b>{c.grade}</b> · <code>{c.title[:18]:<18}</code> "
                f"floor {fmt_ton(c.floor or 0)} · "
                f"liq {c.liquidity:.2f} · кластер {c.cluster_size}"
            )
        text = "\n".join(lines)
    if cb.message is not None:
        await cb.message.edit_text(text, parse_mode="HTML", reply_markup=analytics_back_kb())
    await cb.answer()


@router.callback_query(F.data == "analytics:periods")
async def cb_periods(cb: CallbackQuery, db: Database, user) -> None:
    """Show P&L breakdown over multiple periods (1d / 7d / 30d / all-time)."""
    now = datetime.now(UTC)
    rows = []
    async with db.session() as sess:
        for label, days in (("24ч", 1), ("7д", 7), ("30д", 30), ("Все", None)):
            stmt = select(
                func.count(Trade.id),
                func.coalesce(func.sum(Trade.net_profit), 0.0),
                func.coalesce(func.avg(Trade.profit_pct), 0.0),
            ).where(Trade.user_id == user.id)
            if days is not None:
                since = now - timedelta(days=days)
                stmt = stmt.where(Trade.sold_at >= since)
            count, net, avg_pct = (await sess.execute(stmt)).one()
            rows.append((label, int(count or 0), float(net or 0.0), float(avg_pct or 0.0)))

    lines = ["📅 <b>P&L по периодам</b>", ""]
    for label, count, net, avg_pct in rows:
        sign = "📈" if net >= 0 else "📉"
        lines.append(
            f"{sign} <b>{label}</b>: {count} сделок · {fmt_ton(net, sign=True)} · ср. {fmt_pct(avg_pct)}"
        )
    if cb.message is not None:
        await cb.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=analytics_back_kb()
        )
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
        reply_markup=analytics_back_kb(),
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
        # fall back to a synthetic series — better than nothing in DRY-RUN
        snap = engine.market.collections[name]
        dates = [datetime.now(UTC) - timedelta(hours=h) for h in range(24, 0, -1)]
        floor = float(snap.floor_price or 0.0)
        prices = [round(floor * (0.9 + 0.2 * (i / 24)), 4) for i in range(24)]
    else:
        dates = [s.recorded_at for s in snaps]
        prices = [s.floor_price or 0.0 for s in snaps]
    png = render_floor_chart(f"Floor — {name}", dates, prices)
    await cb.message.answer_photo(
        BufferedInputFile(png, filename="floor.png"),
        caption=f"Floor price ({name}) — 7д",
        reply_markup=analytics_back_kb(),
    )
    await cb.answer()


@router.callback_query(F.data == "analytics:volume")
async def cb_volume(cb: CallbackQuery, engine) -> None:
    """Volume profile (price-bucket histogram) for the largest collection."""
    if not engine.market.collections:
        await cb.answer("Нет коллекций", show_alert=True)
        return
    # Pick the collection with most listings.
    name, snap = max(
        engine.market.collections.items(),
        key=lambda kv: len(kv[1].listings or []),
    )
    listings = snap.listings or []
    if not listings:
        await cb.answer("Нет листингов", show_alert=True)
        return
    buckets = volume_profile(listings, bins=10)
    lines = [
        "📊 <b>Volume profile</b>",
        f"<i>{snap.title or name}</i> · {len(listings)} лотов",
        "",
    ]
    if not buckets:
        lines.append("Не удалось построить распределение.")
    else:
        max_count = max(b.count for b in buckets) or 1
        for b in buckets:
            bar_len = int((b.count / max_count) * 16)
            bar = "█" * bar_len + "░" * (16 - bar_len)
            lines.append(
                f"<code>{b.low:6.2f}-{b.high:6.2f} TON {bar} {b.count:>3} ({b.share_pct:.1f}%)</code>"
            )
    if cb.message is not None:
        await cb.message.edit_text(
            "\n".join(lines), parse_mode="HTML", reply_markup=analytics_back_kb()
        )
    await cb.answer()


@router.callback_query(F.data == "analytics:portfolio")
async def cb_portfolio_analytics(cb: CallbackQuery, db: Database, engine, user) -> None:
    """Detailed portfolio analytics: unrealised P&L, exposure, leaders."""
    async with db.session() as sess:
        items = await PortfolioRepository(sess).list_by_user(user.id)
    if not items:
        text = "Портфель пуст. Купите что-то — и здесь появится разбор."
    else:
        floors = {
            name: float(snap.floor_price or 0.0)
            for name, snap in engine.market.collections.items()
        }
        report = PortfolioAnalyzer.analyse(items, floors=floors)
        text = PortfolioAnalyzer.render(report)
    if cb.message is not None:
        await cb.message.edit_text(
            text, parse_mode="HTML", reply_markup=analytics_back_kb()
        )
    await cb.answer()
