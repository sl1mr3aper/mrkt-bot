"""Portfolio details (manual sell etc.)."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

router = Router(name="portfolio_extra")


@router.callback_query(F.data.startswith("portfolio:"))
async def cb_portfolio_action(cb: CallbackQuery, state: FSMContext) -> None:
    # Placeholder for advanced portfolio actions wired in future.
    await cb.answer("Действие не реализовано")
