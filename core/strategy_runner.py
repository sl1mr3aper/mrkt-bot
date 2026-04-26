"""Runs registered strategies against incoming gift candidates."""

from __future__ import annotations

import json
from typing import Any

from db.database import Database
from db.repositories import StrategyRepository
from strategies import STRATEGY_REGISTRY
from strategies.base import BaseStrategy, BuyDecision
from utils.logger import get_logger

log = get_logger(__name__)


class StrategyRunner:
    """Loads, instantiates, and queries persisted strategies."""

    def __init__(self, analyzer: Any, db: Database) -> None:
        self.analyzer = analyzer
        self.db = db
        self._cache: dict[int, BaseStrategy] = {}

    def _instantiate(self, type_: str, params: dict[str, Any]) -> BaseStrategy | None:
        cls = STRATEGY_REGISTRY.get(type_)
        if not cls:
            log.warning("Unknown strategy type: {}", type_)
            return None
        try:
            return cls(params=params, analyzer=self.analyzer)
        except Exception as exc:  # pragma: no cover - misconfigured params
            log.error("Failed to init strategy {}: {}", type_, exc)
            return None

    async def list_active(self, user_id: int) -> list[tuple[int, BaseStrategy]]:
        async with self.db.session() as sess:
            repo = StrategyRepository(sess)
            rows = await repo.list_active(user_id)
        out: list[tuple[int, BaseStrategy]] = []
        for row in rows:
            try:
                params = json.loads(row.params or "{}")
            except json.JSONDecodeError:
                params = {}
            inst = self._instantiate(row.type, params)
            if inst:
                inst.id = row.id
                inst.name = row.name
                out.append((row.id, inst))
        return out

    def evaluate_all(
        self,
        gift: dict[str, Any],
        analysis: Any,
        user_state: dict[str, Any],
        strategies: list[tuple[int, BaseStrategy]],
    ) -> list[BuyDecision]:
        results: list[BuyDecision] = []
        for sid, strat in strategies:
            try:
                decision = strat.should_buy(
                    gift=gift, analysis=analysis, user_state=user_state
                )
            except Exception as exc:
                log.exception("strategy {} crashed: {}", strat.name, exc)
                continue
            decision.strategy_id = sid
            decision.strategy_name = strat.name
            results.append(decision)
        return results
