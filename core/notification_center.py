"""Centralised notification builder + dispatcher.

Wraps the bot's notify callback so the rest of the codebase emits structured
events (``buy_filled``, ``sold``, ``stop_loss``, ``alert``, ``error``) instead
of free-form strings. Persists every notification to the DB for replay.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from db.database import Database
from db.repositories import NotificationRepository
from utils.formatters import fmt_pct, fmt_ton
from utils.logger import get_logger

log = get_logger(__name__)

NotifyFn = Callable[[int, str], Awaitable[None]]


@dataclass
class NotifyEvent:
    user_id: int
    telegram_id: int
    kind: str
    title: str
    body: str
    extras: dict[str, Any]


class NotificationCenter:
    """High-level notification API used across handlers + tasks.

    The DB layer keeps a copy of every emitted notification so the user can
    review history later via the bot UI even after restart.
    """

    def __init__(self, *, db: Database, notify: NotifyFn | None) -> None:
        self.db = db
        self._notify = notify
        self._kind_emojis = {
            "buy_filled": "🟢",
            "sold": "💸",
            "stop_loss": "🛑",
            "alert": "🔔",
            "error": "❌",
            "info": "ℹ️",
            "warning": "⚠️",
        }

    # ─── public API ────────────────────────────────────────

    async def emit(
        self,
        *,
        user_id: int,
        telegram_id: int,
        kind: str,
        title: str,
        body: str,
        **extras: Any,
    ) -> None:
        text = self._format(kind, title, body)
        async with self.db.session() as sess:
            await NotificationRepository(sess).add(
                user_id=user_id, kind=kind, title=title, body=body
            )
        if self._notify is not None:
            try:
                await self._notify(telegram_id, text)
            except Exception as exc:  # pragma: no cover — defensive
                log.warning("notification send failed: {}", exc)

    async def buy_filled(
        self,
        *,
        user_id: int,
        telegram_id: int,
        gift_name: str,
        collection: str,
        price: float,
        target_sell: float | None = None,
        rarity: float | None = None,
    ) -> None:
        body = (
            f"<b>{gift_name}</b> ({collection})\n"
            f"💰 Куплено за {fmt_ton(price)}"
        )
        if rarity:
            body += f"\n⭐ Rarity: {rarity:.2f}"
        if target_sell:
            body += f"\n🎯 Цель: {fmt_ton(target_sell)} (+{fmt_pct((target_sell - price) / price * 100)})"
        await self.emit(
            user_id=user_id,
            telegram_id=telegram_id,
            kind="buy_filled",
            title=f"Куплено: {gift_name}",
            body=body,
        )

    async def sold(
        self,
        *,
        user_id: int,
        telegram_id: int,
        gift_name: str,
        buy_price: float,
        sell_price: float,
        net_profit: float,
    ) -> None:
        pct = (net_profit / buy_price) * 100 if buy_price else 0.0
        body = (
            f"<b>{gift_name}</b>\n"
            f"📤 Продано за {fmt_ton(sell_price)} (купили за {fmt_ton(buy_price)})\n"
            f"💵 P&L: {fmt_ton(net_profit, sign=True)} ({fmt_pct(pct)})"
        )
        await self.emit(
            user_id=user_id,
            telegram_id=telegram_id,
            kind="sold",
            title=f"Продано: {gift_name}",
            body=body,
        )

    async def stop_loss(
        self,
        *,
        user_id: int,
        telegram_id: int,
        gift_name: str,
        loss: float,
    ) -> None:
        body = f"🛑 Стоп-лосс по <b>{gift_name}</b>: {fmt_ton(loss, sign=True)}"
        await self.emit(
            user_id=user_id,
            telegram_id=telegram_id,
            kind="stop_loss",
            title="Стоп-лосс",
            body=body,
        )

    async def alert(
        self,
        *,
        user_id: int,
        telegram_id: int,
        title: str,
        body: str,
    ) -> None:
        await self.emit(
            user_id=user_id,
            telegram_id=telegram_id,
            kind="alert",
            title=title,
            body=body,
        )

    async def error(
        self,
        *,
        user_id: int,
        telegram_id: int,
        title: str,
        body: str,
    ) -> None:
        await self.emit(
            user_id=user_id,
            telegram_id=telegram_id,
            kind="error",
            title=title,
            body=body,
        )

    # ─── internals ─────────────────────────────────────────

    def _format(self, kind: str, title: str, body: str) -> str:
        emoji = self._kind_emojis.get(kind, "🔹")
        ts = datetime.now(UTC).strftime("%H:%M:%S")
        return f"{emoji} <b>{title}</b>  <i>{ts}</i>\n\n{body}"
