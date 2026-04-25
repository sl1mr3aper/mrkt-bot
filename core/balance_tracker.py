"""Periodically refreshes user balance from MRKT API."""

from __future__ import annotations

import time
from typing import Any

from utils.logger import get_logger

log = get_logger(__name__)


class BalanceTracker:
    """Caches the user's balance and refreshes from the API on demand."""

    def __init__(self, client: Any, market_state: Any, ttl_seconds: float = 30.0) -> None:
        self.client = client
        self.state = market_state
        self.ttl = ttl_seconds
        self._last_fetch = 0.0

    async def refresh(self, *, force: bool = False) -> float:
        now = time.time()
        if not force and (now - self._last_fetch) < self.ttl and self.state.balance_ton:
            return self.state.balance_ton

        balance = await self.client.get_balance_ton()
        self.state.set_balance(balance)
        self._last_fetch = now
        log.debug("Balance refreshed: {:.4f} TON", balance)
        return balance

    @property
    def balance(self) -> float:
        return self.state.balance_ton
