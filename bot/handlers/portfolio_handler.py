"""Portfolio extras: CSV export and (future) manual sell actions."""

from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery

from db.database import Database
from db.repositories import PortfolioRepository, TradeRepository
from utils.csv_export import export_portfolio, export_trades

router = Router(name="portfolio_extra")


@router.callback_query(F.data == "portfolio:export")
async def cb_portfolio_export(cb: CallbackQuery, db: Database, user) -> None:
    async with db.session() as sess:
        items = await PortfolioRepository(sess).list_by_user(user.id)
    blob = export_portfolio(items)
    fname = f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    if cb.message is not None:
        await cb.message.answer_document(
            BufferedInputFile(blob, filename=fname),
            caption=f"📦 {len(items)} позиций",
        )
    await cb.answer()


@router.callback_query(F.data == "portfolio:export_trades")
async def cb_trades_export(cb: CallbackQuery, db: Database, user) -> None:
    async with db.session() as sess:
        trades = await TradeRepository(sess).list_by_user(user.id, limit=10_000)
    blob = export_trades(trades)
    fname = f"trades_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    if cb.message is not None:
        await cb.message.answer_document(
            BufferedInputFile(blob, filename=fname),
            caption=f"📜 {len(trades)} сделок",
        )
    await cb.answer()


@router.callback_query(F.data.startswith("portfolio:"))
async def cb_portfolio_fallback(cb: CallbackQuery) -> None:
    await cb.answer("Действие не реализовано", show_alert=True)
