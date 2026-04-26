"""Strategy CRUD."""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Strategy


class StrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        name: str,
        type_: str,
        params: dict[str, object],
        filter_id: int | None = None,
        is_active: bool = False,
    ) -> Strategy:
        strat = Strategy(
            user_id=user_id,
            name=name,
            type=type_,
            params=json.dumps(params),
            filter_id=filter_id,
            is_active=is_active,
        )
        self.session.add(strat)
        await self.session.flush()
        return strat

    async def get(self, strategy_id: int) -> Strategy | None:
        return await self.session.get(Strategy, strategy_id)

    async def list_by_user(self, user_id: int) -> list[Strategy]:
        result = await self.session.execute(
            select(Strategy)
            .where(Strategy.user_id == user_id)
            .order_by(Strategy.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active(self, user_id: int) -> list[Strategy]:
        result = await self.session.execute(
            select(Strategy).where(
                Strategy.user_id == user_id, Strategy.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def set_active(self, strategy_id: int, active: bool) -> None:
        strat = await self.get(strategy_id)
        if strat:
            strat.is_active = active

    async def delete(self, strategy_id: int) -> None:
        strat = await self.get(strategy_id)
        if strat:
            await self.session.delete(strat)

    async def update_params(self, strategy_id: int, params: dict[str, object]) -> None:
        strat = await self.get(strategy_id)
        if strat:
            strat.params = json.dumps(params)
