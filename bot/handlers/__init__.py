"""Aiogram 3 routers (one per feature)."""

from .analytics_handler import router as analytics_router
from .filters_handler import router as filters_router
from .main_handler import router as main_router
from .portfolio_handler import router as portfolio_router
from .search_handler import router as search_router
from .settings_handler import router as settings_router
from .strategy_handler import router as strategy_router
from .trading_handler import router as trading_router

ALL_ROUTERS = [
    main_router,
    filters_router,
    search_router,
    trading_router,
    portfolio_router,
    strategy_router,
    analytics_router,
    settings_router,
]

__all__ = ["ALL_ROUTERS"]
