"""Entry point — bootstraps the bot, DB, MRKT client, and background tasks."""

from __future__ import annotations

import asyncio
import signal
from contextlib import suppress

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot import build_dispatcher
from config import settings
from core import AuthManager, MrktClient, TradingEngine
from db.database import init_db
from tasks import TaskManager
from tasks.analytics_reporter import AnalyticsReporter
from tasks.health_checker import HealthChecker
from tasks.market_monitor import MarketMonitor
from tasks.order_watcher import OrderWatcher
from tasks.price_parser import PriceParser
from tasks.stop_loss_monitor import StopLossMonitor
from tasks.token_refresher import TokenRefresher
from utils.logger import get_logger, setup_logger


async def amain() -> None:
    import os

    # Enable demo trades seeding for first-run users when running w/o MRKT creds.
    if not settings.MRKT_API_ID or not settings.MRKT_API_HASH:
        os.environ.setdefault("MRKT_DEMO_DATA", "1")
    settings.ensure_dirs()
    setup_logger(
        level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE,
        rotation=settings.LOG_ROTATION,
        retention=settings.LOG_RETENTION,
    )
    log = get_logger("main")
    log.info("Starting MRKT trading bot — DRY_RUN={}", settings.DRY_RUN)

    if not settings.BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is required (see .env.example)")
    if not settings.MRKT_API_ID or not settings.MRKT_API_HASH:
        log.warning(
            "MRKT_API_ID/MRKT_API_HASH not set — auto-trading will fail until provided"
        )

    db = init_db(settings.database_url)
    await db.create_all()

    bot = Bot(
        settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    me = await bot.get_me()
    log.info("Bot @{} ready", me.username)

    notify_sem = asyncio.Semaphore(5)

    async def notify(telegram_id: int, text: str) -> None:
        async with notify_sem:
            try:
                await bot.send_message(telegram_id, text, disable_web_page_preview=True)
            except Exception as exc:
                log.warning("notify failed: {}", exc)

    if settings.MRKT_API_ID and settings.MRKT_API_HASH:
        client = MrktClient(
            api_id=settings.MRKT_API_ID,
            api_hash=settings.MRKT_API_HASH,
            session_name=settings.SESSION_NAME,
            workdir=".",
            proxy=settings.PROXY_URL,
            proxy_api_only=settings.PROXY_API_ONLY,
            impersonate=settings.TLS_IMPERSONATE,
        )
        with suppress(Exception):
            await client.ensure_auth()
    else:
        from core.mrkt_client import MockMrktClient

        client = MockMrktClient()  # type: ignore[assignment]

    auth = AuthManager(client, refresh_hours=settings.TOKEN_REFRESH_HOURS)
    engine = TradingEngine(client=client, db=db, config=settings, notify=notify)

    # Pre-warm the in-memory market state so analytics are populated even
    # before the background monitor catches up.
    with suppress(Exception):
        await engine.refresh_collections()
        from collections import defaultdict
        listings_by = defaultdict(list)
        for lst in getattr(client, "gifts", []) or []:
            listings_by[lst.get("collection")].append(lst)
        for name, items in listings_by.items():
            engine.market.update_collection(
                name,
                min((float(i.get("price") or 0.0) for i in items), default=0.0),
                listings=items,
            )

    tm = TaskManager()
    tm.spawn("market_monitor", MarketMonitor(
        engine, db, client,
        min_interval=settings.MONITOR_INTERVAL_MIN,
        max_interval=settings.MONITOR_INTERVAL_MAX,
    ).run_forever)
    tm.spawn("order_watcher", OrderWatcher(
        engine, db, client,
        notify=notify,
        stuck_minutes=settings.ORDER_TIMEOUT_MINUTES,
    ).run_forever)
    tm.spawn("token_refresher", TokenRefresher(auth, settings.TOKEN_REFRESH_HOURS).run_forever)
    tm.spawn("price_parser", PriceParser(engine, db, settings.PRICE_PARSE_MINUTES).run_forever)
    tm.spawn("stop_loss_monitor", StopLossMonitor(engine, db).run_forever)
    tm.spawn("analytics_reporter", AnalyticsReporter(engine, db, notify=notify).run_forever)
    tm.spawn("health_checker", HealthChecker(engine).run_forever)
    from tasks.watchlist_alerter import WatchlistAlerter
    tm.spawn(
        "watchlist_alerter",
        WatchlistAlerter(engine, db, notify=notify).run_forever,
    )

    dp = build_dispatcher(db=db, engine=engine)

    stop_event = asyncio.Event()

    def _signal(*_: object) -> None:
        log.info("Signal received, shutting down…")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _signal)

    polling_task = asyncio.create_task(dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()))

    try:
        await stop_event.wait()
    finally:
        log.info("Stopping…")
        polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await polling_task
        await tm.stop_all()
        await client.close()
        await db.dispose()
        await bot.session.close()
        log.info("Bye.")


def main() -> None:
    try:
        asyncio.run(amain())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
