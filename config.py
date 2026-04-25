"""Application configuration loaded from environment / .env."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Centralised configuration. All values are overridable via env vars."""

    # ─── Telegram ───────────────────────────────────────────
    BOT_TOKEN: str = Field(default="", description="Telegram bot token")
    ADMIN_ID: int = Field(default=0, description="Admin telegram user id")

    # ─── MRKT auth ──────────────────────────────────────────
    MRKT_API_ID: int = Field(default=0)
    MRKT_API_HASH: str = Field(default="")
    SESSION_NAME: str = "mrkt_session"

    # ─── Proxy ──────────────────────────────────────────────
    PROXY_URL: str | None = None
    PROXY_API_ONLY: bool = True
    TLS_IMPERSONATE: str = "chrome124"

    # ─── Trading ────────────────────────────────────────────
    DRY_RUN: bool = True
    STOP_LOSS_PCT: float = 15.0
    MAX_BUY_TON: float = 10.0
    MIN_PROFIT_TON: float = 0.05
    MARKET_COMMISSION_PCT: float = 5.0
    LARGE_DEAL_TON: float = 5.0
    MAX_DAILY_LOSS_TON: float = 20.0
    MAX_DAILY_TRADES: int = 50

    # ─── Timings ────────────────────────────────────────────
    COOLDOWN_SECONDS: int = 60
    ORDER_TIMEOUT_MINUTES: int = 5
    MONITOR_INTERVAL_MIN: int = 20
    MONITOR_INTERVAL_MAX: int = 60
    TOKEN_REFRESH_HOURS: int = 20
    PRICE_PARSE_MINUTES: int = 30

    # ─── Database ───────────────────────────────────────────
    DATABASE_PATH: str = "data/mrkt_bot.db"

    # ─── Logging ────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/bot.log"
    LOG_ROTATION: str = "1 day"
    LOG_RETENTION: str = "30 days"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """SQLAlchemy async URL."""
        return f"sqlite+aiosqlite:///{self.DATABASE_PATH}"

    @property
    def commission(self) -> float:
        """Commission as fraction (0.05 = 5%)."""
        return self.MARKET_COMMISSION_PCT / 100.0

    def ensure_dirs(self) -> None:
        """Create directories needed for runtime (db, logs)."""
        for path in (self.DATABASE_PATH, self.LOG_FILE):
            Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)


# Module-level singleton — re-exported by `from config import settings`.
settings = Config()
