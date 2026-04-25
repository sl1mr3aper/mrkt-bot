"""Main trading engine — wires together the API client, strategies, DB, etc."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

from analytics.rarity_calculator import RarityCalculator
from db.database import Database
from db.repositories import (
    PortfolioRepository,
    PriceRepository,
    TradeRepository,
    UserRepository,
)
from utils.exceptions import InsufficientBalanceError, MrktBotError
from utils.formatters import (
    fmt_buy_success,
    fmt_dry_run,
    fmt_human_duration,
    fmt_listed,
    fmt_sell_success,
    fmt_stop_loss,
)
from utils.logger import get_logger

from .balance_tracker import BalanceTracker
from .cooldown_manager import CooldownManager
from .market_state import MarketState
from .order_manager import OrderManager
from .price_analyzer import PriceAnalyzer, TradeAnalysis
from .profit_tracker import ProfitTracker
from .stop_loss import StopLossAction, StopLossEngine
from .strategy_runner import StrategyRunner

log = get_logger(__name__)


NotifyFn = Callable[[int, str], Coroutine[Any, Any, None]]


class TradingEngine:
    """Orchestrates market scan, decisions, execution, and notifications."""

    def __init__(
        self,
        *,
        client: Any,
        db: Database,
        config: Any,
        notify: NotifyFn,
    ) -> None:
        self.client = client
        self.db = db
        self.cfg = config
        self.notify = notify

        self.market = MarketState()
        self.cooldown = CooldownManager(default_seconds=config.COOLDOWN_SECONDS)
        self.profit = ProfitTracker()
        self.balance = BalanceTracker(client, self.market)
        self.rarity = RarityCalculator()
        self.analyzer = PriceAnalyzer(
            commission=config.commission, rarity=self.rarity
        )
        self.orders = OrderManager(db)
        self.strategy_runner = StrategyRunner(self.analyzer, db)
        self.stop_loss = StopLossEngine(commission=config.commission)

        self._running = False

    # ─── helpers ──────────────────────────────────────────

    async def refresh_collections(self) -> list[dict[str, Any]]:
        collections = await self.client.list_collections()
        for c in collections:
            self.market.update_collection(c["name"], c["floor_price"], c.get("volume", 0))
        return collections

    async def refresh_balance(self, force: bool = False) -> float:
        return await self.balance.refresh(force=force)

    # ─── decision pipeline ────────────────────────────────

    def _user_state(self, user: Any) -> dict[str, Any]:
        return {
            "balance_ton": self.market.balance_ton,
            "active_positions": 0,  # filled on the fly when needed
            "daily_buys": self.market.daily_buys,
            "daily_loss": self.market.daily_loss,
            "min_profit_ton": user.min_profit_ton,
            "max_buy_ton": user.max_buy_ton,
            "max_daily_trades": user.max_daily_trades,
            "max_daily_loss_ton": user.max_daily_loss_ton,
            "stop_loss_pct": user.stop_loss_pct,
            "commission": self.cfg.commission,
        }

    async def _passes_global_checks(
        self,
        *,
        user: Any,
        gift: dict[str, Any],
        analysis: TradeAnalysis,
    ) -> tuple[bool, str]:
        price = float(gift.get("price") or 0.0)

        if not self.market.has_balance_for(price):
            return False, "Недостаточно баланса"
        if analysis.expected_profit < user.min_profit_ton:
            return False, "Прибыль слишком мала"
        if price > user.max_buy_ton:
            return False, "Цена выше максимально допустимой"
        if self.market.daily_buys >= user.max_daily_trades:
            return False, "Дневной лимит сделок"
        if self.market.daily_loss >= user.max_daily_loss_ton:
            return False, "Превышен дневной лимит убытков"
        if gift.get("id") and await self.orders.is_in_flight(user.id, gift["id"]):
            return False, "Уже есть в портфеле/ордерах"
        return True, "OK"

    # ─── execution ────────────────────────────────────────

    async def execute_buy(
        self,
        *,
        user: Any,
        gift: dict[str, Any],
        analysis: TradeAnalysis,
        strategy_id: int | None,
        strategy_name: str,
    ) -> int | None:
        price = float(gift.get("price") or 0.0)
        target_sell = self.analyzer.calculate_sell_price(
            buy_price=price,
            floor_price=analysis.floor,
            fair_value=analysis.fair_value,
            rarity_score=analysis.rarity_score,
        )

        if user.dry_run:
            await self.notify(
                user.telegram_id,
                fmt_dry_run({
                    "gift_name": gift.get("name") or gift.get("title"),
                    "buy_price": price,
                    "expected_profit": analysis.expected_profit,
                    "expected_profit_pct": analysis.expected_profit_pct,
                    "time": datetime.now(UTC),
                }),
            )
            await self.orders.record_buy(
                user_id=user.id,
                strategy_id=strategy_id,
                gift={**gift, "rarity_score": analysis.rarity_score},
                price=price,
                target_price=target_sell,
                dry_run=True,
            )
            return None

        try:
            if gift.get("id"):
                await self.client.buy([gift["id"]])
        except InsufficientBalanceError as exc:
            log.warning("Buy aborted: {}", exc)
            return None
        except MrktBotError as exc:
            log.error("Buy failed: {}", exc)
            return None

        order_id = await self.orders.record_buy(
            user_id=user.id,
            strategy_id=strategy_id,
            gift={**gift, "rarity_score": analysis.rarity_score},
            price=price,
            target_price=target_sell,
            dry_run=False,
        )
        # Add to portfolio + start cooldown
        async with self.db.session() as sess:
            await PortfolioRepository(sess).add(
                user_id=user.id,
                gift_id=gift["id"],
                gift_name=gift.get("name") or gift.get("title"),
                collection=gift.get("collection"),
                model=gift.get("model"),
                backdrop=gift.get("backdrop"),
                symbol=gift.get("symbol"),
                rarity_score=analysis.rarity_score,
                number=gift.get("number"),
                buy_price=price,
                buy_order_id=order_id,
                target_sell=target_sell,
                stop_loss_price=self.stop_loss.stop_loss_price(price, user.stop_loss_pct),
                cooldown_until=datetime.now(UTC) + timedelta(seconds=self.cfg.COOLDOWN_SECONDS),
                strategy_id=strategy_id,
            )
        if gift.get("id"):
            self.cooldown.start(gift["id"], self.cfg.COOLDOWN_SECONDS)
        self.market.increment_daily_buys()
        await self.balance.refresh(force=True)
        await self.notify(
            user.telegram_id,
            fmt_buy_success({
                "gift_name": gift.get("name") or gift.get("title"),
                "collection": gift.get("collection"),
                "model": gift.get("model"),
                "backdrop": gift.get("backdrop"),
                "symbol": gift.get("symbol"),
                "model_pct": gift.get("modelRarity"),
                "backdrop_pct": gift.get("backdropRarity"),
                "symbol_pct": gift.get("symbolRarity"),
                "rarity_score": analysis.rarity_score,
                "number": gift.get("number"),
                "buy_price": price,
                "target_sell": target_sell,
                "expected_profit": analysis.expected_profit,
                "expected_profit_pct": analysis.expected_profit_pct,
                "cooldown_sec": self.cfg.COOLDOWN_SECONDS,
                "balance_after": self.market.balance_ton,
                "strategy": strategy_name,
                "time": datetime.now(UTC),
            }),
        )
        return order_id

    async def list_for_sale_after_cooldown(
        self,
        *,
        user: Any,
        gift_id: str,
        sell_price: float,
    ) -> None:
        await self.cooldown.wait(gift_id)
        if user.dry_run:
            return

        try:
            await self.client.list_for_sale([gift_id], [sell_price])
        except MrktBotError as exc:
            log.error("Listing failed for {}: {}", gift_id, exc)
            return

        async with self.db.session() as sess:
            portfolio = PortfolioRepository(sess)
            item = await portfolio.get(gift_id)
            if item:
                item.listed_at = datetime.now(UTC)
            await self.orders.record_sell(
                user_id=user.id,
                gift={
                    "id": gift_id,
                    "name": item.gift_name if item else "",
                    "collection": item.collection if item else "",
                    "rarity_score": item.rarity_score if item else None,
                },
                price=sell_price,
                strategy_id=item.strategy_id if item else None,
                dry_run=False,
            )

        await self.notify(
            user.telegram_id,
            fmt_listed({
                "gift_name": item.gift_name if item else gift_id,
                "rarity_score": item.rarity_score if item else None,
                "buy_price": item.buy_price if item else 0.0,
                "sell_price": sell_price,
                "expected_profit": (sell_price - (item.buy_price if item else 0.0)) if item else 0.0,
                "expected_profit_pct": (
                    ((sell_price - item.buy_price) / item.buy_price * 100.0)
                    if item and item.buy_price
                    else 0.0
                ),
                "stop_loss_price": item.stop_loss_price if item else None,
                "time": datetime.now(UTC),
            }),
        )

    async def settle_sale(
        self,
        *,
        user: Any,
        gift_id: str,
        sell_price: float,
        is_stop_loss: bool = False,
    ) -> None:
        async with self.db.session() as sess:
            portfolio = PortfolioRepository(sess)
            item = await portfolio.get(gift_id)
            if not item:
                return
            commission = sell_price * self.cfg.commission
            gross = sell_price - item.buy_price
            net = gross - commission
            profit_pct = (net / item.buy_price * 100.0) if item.buy_price else 0.0
            held_at = item.bought_at
            if held_at and held_at.tzinfo is None:
                held_at = held_at.replace(tzinfo=UTC)
            held_sec = (
                int((datetime.now(UTC) - held_at).total_seconds())
                if held_at
                else 0
            )

            await TradeRepository(sess).add(
                user_id=user.id,
                gift_id=gift_id,
                gift_name=item.gift_name,
                collection=item.collection,
                rarity_score=item.rarity_score,
                buy_price=item.buy_price,
                sell_price=sell_price,
                commission=commission,
                gross_profit=gross,
                net_profit=net,
                profit_pct=profit_pct,
                hold_time_sec=held_sec,
                strategy_id=item.strategy_id,
                dry_run=False,
                is_stop_loss=is_stop_loss,
                bought_at=item.bought_at,
            )
            await portfolio.remove(gift_id)

        self.profit.record_trade(net_profit=net, is_stop_loss=is_stop_loss)
        await self.balance.refresh(force=True)
        await self.notify(
            user.telegram_id,
            fmt_sell_success({
                "gift_name": item.gift_name,
                "rarity_score": item.rarity_score,
                "buy_price": item.buy_price,
                "sell_price": sell_price,
                "commission": commission,
                "net_profit": net,
                "profit_pct": profit_pct,
                "hold_time_human": fmt_human_duration(held_sec),
                "balance_after": self.market.balance_ton,
                "daily_profit": self.profit.stats.daily_profit,
                "all_time_profit": self.profit.stats.all_time_profit,
                "time": datetime.now(UTC),
            }),
        )

    # ─── stop loss enforcement ────────────────────────────

    async def enforce_stop_loss_for_user(self, user: Any) -> None:
        async with self.db.session() as sess:
            items = await PortfolioRepository(sess).list_by_user(user.id)
        for item in items:
            current_floor = self.market.floor(item.collection or "")
            if current_floor <= 0:
                continue
            decision = self.stop_loss.evaluate(
                buy_price=item.buy_price,
                current_floor=current_floor,
                bought_at=item.bought_at or datetime.now(UTC),
                stop_loss_pct=user.stop_loss_pct,
            )
            if decision.action != StopLossAction.SELL_NOW:
                continue
            if user.dry_run:
                continue
            try:
                await self.client.cancel_sale([item.gift_id])
            except MrktBotError:
                pass
            try:
                await self.client.list_for_sale([item.gift_id], [decision.sell_at])
            except MrktBotError as exc:
                log.error("Stop-loss listing failed: {}", exc)
                continue
            self.market.add_daily_loss(item.buy_price - decision.sell_at)
            await self.notify(
                user.telegram_id,
                fmt_stop_loss({
                    "gift_name": item.gift_name,
                    "buy_price": item.buy_price,
                    "current_floor": current_floor,
                    "floor_change_pct": decision.floor_change_pct,
                    "stop_threshold": decision.stop_threshold,
                    "sell_at": decision.sell_at,
                    "loss": decision.sell_at - item.buy_price,
                    "loss_pct": (
                        (decision.sell_at - item.buy_price) / item.buy_price * 100.0
                    ),
                    "balance_after": self.market.balance_ton,
                    "time": datetime.now(UTC),
                }),
            )

    # ─── price snapshot ───────────────────────────────────

    async def record_price_snapshot(self, collection: str) -> None:
        listings = self.market.listings(collection)
        prices = [l.get("price") for l in listings if l.get("price") is not None]
        if not prices:
            return
        avg_price = sum(prices) / len(prices)
        async with self.db.session() as sess:
            await PriceRepository(sess).add_snapshot(
                collection=collection,
                floor_price=min(prices),
                volume_count=len(listings),
                min_price=min(prices),
                max_price=max(prices),
                avg_price=avg_price,
            )

    # ─── lifecycle ────────────────────────────────────────

    async def aggregate_pnl(self, user_id: int) -> None:
        """Sync persistent stats with profit_tracker (called on startup)."""
        async with self.db.session() as sess:
            all_time = await TradeRepository(sess).all_time_profit(user_id)
        self.profit.set_all_time(all_time)

    async def reset_active_user(self, telegram_id: int, username: str | None) -> Any:
        async with self.db.session() as sess:
            return await UserRepository(sess).get_or_create(telegram_id, username)
