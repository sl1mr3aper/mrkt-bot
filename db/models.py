"""SQLAlchemy ORM models — full persistence layer."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    """Bot user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Trading settings
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    stop_loss_pct: Mapped[float] = mapped_column(Float, default=15.0)
    max_buy_ton: Mapped[float] = mapped_column(Float, default=10.0)
    min_profit_ton: Mapped[float] = mapped_column(Float, default=0.05)
    large_deal_ton: Mapped[float] = mapped_column(Float, default=5.0)
    max_daily_loss_ton: Mapped[float] = mapped_column(Float, default=20.0)
    max_daily_trades: Mapped[int] = mapped_column(Integer, default=50)

    proxy_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notifications: Mapped[str] = mapped_column(Text, default="{}")  # JSON

    auto_trading: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    filters: Mapped[list[UserFilter]] = relationship(back_populates="user")
    strategies: Mapped[list[Strategy]] = relationship(back_populates="user")


class UserFilter(Base):
    """Active filter set for searching gifts."""

    __tablename__ = "user_filters"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    collection_names: Mapped[str] = mapped_column(Text, default="[]")  # JSON
    model_names: Mapped[str] = mapped_column(Text, default="[]")
    backdrop_names: Mapped[str] = mapped_column(Text, default="[]")
    symbol_names: Mapped[str] = mapped_column(Text, default="[]")

    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    ordering: Mapped[str] = mapped_column(String(32), default="Price")
    low_to_high: Mapped[bool] = mapped_column(Boolean, default=True)
    mintable_only: Mapped[bool] = mapped_column(Boolean, default=False)
    number_filter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rarity_min: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="filters")


class Strategy(Base):
    """Trading strategy persisted between runs."""

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(64))  # FloorMultiplier, etc.
    params: Mapped[str] = mapped_column(Text, default="{}")  # JSON
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    filter_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_filters.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="strategies")


class Order(Base):
    """Buy/Sell order placed (or simulated) by the engine."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategies.id"), nullable=True
    )

    order_type: Mapped[str] = mapped_column(String(8))  # buy | sell
    gift_id: Mapped[str | None] = mapped_column(String(64), index=True)
    gift_name: Mapped[str | None] = mapped_column(String(128))
    collection: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(64))
    backdrop: Mapped[str | None] = mapped_column(String(64))
    symbol: Mapped[str | None] = mapped_column(String(64))

    model_rarity: Mapped[float | None] = mapped_column(Float)
    backdrop_rarity: Mapped[float | None] = mapped_column(Float)
    symbol_rarity: Mapped[float | None] = mapped_column(Float)
    rarity_score: Mapped[float | None] = mapped_column(Float)
    number: Mapped[int | None] = mapped_column(Integer)

    price: Mapped[float] = mapped_column(Float)
    target_price: Mapped[float | None] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String(16), default="active")
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_orders_user_status", "user_id", "status"),
    )


class PortfolioItem(Base):
    """A gift currently owned and waiting to be sold."""

    __tablename__ = "portfolio"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    gift_id: Mapped[str] = mapped_column(String(64), unique=True)
    gift_name: Mapped[str | None] = mapped_column(String(128))
    collection: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(64))
    backdrop: Mapped[str | None] = mapped_column(String(64))
    symbol: Mapped[str | None] = mapped_column(String(64))
    rarity_score: Mapped[float | None] = mapped_column(Float)
    number: Mapped[int | None] = mapped_column(Integer)

    buy_price: Mapped[float] = mapped_column(Float)
    buy_order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    target_sell: Mapped[float | None] = mapped_column(Float)
    stop_loss_price: Mapped[float | None] = mapped_column(Float)

    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    bought_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    listed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategies.id"), nullable=True
    )


class Trade(Base):
    """Completed buy→sell cycle."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    gift_id: Mapped[str | None] = mapped_column(String(64))
    gift_name: Mapped[str | None] = mapped_column(String(128))
    collection: Mapped[str | None] = mapped_column(String(64))
    rarity_score: Mapped[float | None] = mapped_column(Float)

    buy_price: Mapped[float] = mapped_column(Float)
    sell_price: Mapped[float] = mapped_column(Float)
    commission: Mapped[float] = mapped_column(Float, default=0.0)
    gross_profit: Mapped[float] = mapped_column(Float, default=0.0)
    net_profit: Mapped[float] = mapped_column(Float, default=0.0)
    profit_pct: Mapped[float] = mapped_column(Float, default=0.0)
    hold_time_sec: Mapped[int] = mapped_column(Integer, default=0)

    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategies.id"), nullable=True
    )
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False)
    is_stop_loss: Mapped[bool] = mapped_column(Boolean, default=False)

    bought_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sold_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_trades_user_date", "user_id", "sold_at"),
    )


class PriceHistory(Base):
    """Floor / volume snapshots over time."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    collection: Mapped[str] = mapped_column(String(64), index=True)
    model: Mapped[str | None] = mapped_column(String(64))
    floor_price: Mapped[float | None] = mapped_column(Float)
    min_price: Mapped[float | None] = mapped_column(Float)
    max_price: Mapped[float | None] = mapped_column(Float)
    avg_price: Mapped[float | None] = mapped_column(Float)
    volume_count: Mapped[int] = mapped_column(Integer, default=0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_price_history_collection", "collection", "recorded_at"),
    )


class SystemLog(Base):
    """Persistent log table for audit / debugging."""

    __tablename__ = "system_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(16))
    module: Mapped[str] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text)
    data: Mapped[str | None] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
