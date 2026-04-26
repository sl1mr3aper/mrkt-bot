"""CRUD repositories for each domain entity."""

from .notification_repo import NotificationRepository
from .order_repo import OrderRepository
from .portfolio_repo import PortfolioRepository
from .price_repo import PriceRepository
from .strategy_repo import StrategyRepository
from .trade_repo import TradeRepository
from .user_repo import UserRepository
from .watchlist_repo import WatchlistRepository

__all__ = [
    "NotificationRepository",
    "OrderRepository",
    "PortfolioRepository",
    "PriceRepository",
    "StrategyRepository",
    "TradeRepository",
    "UserRepository",
    "WatchlistRepository",
]
