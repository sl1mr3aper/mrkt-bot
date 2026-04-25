"""All FSM state groups in one module to avoid noise."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class MainMenuSG(StatesGroup):
    main = State()


class CollectionsSG(StatesGroup):
    list = State()
    selected = State()


class FiltersSG(StatesGroup):
    menu = State()
    models = State()
    backdrops = State()
    symbols = State()
    price_min = State()
    price_max = State()
    rarity = State()
    ordering = State()
    number = State()


class SearchSG(StatesGroup):
    results = State()
    gift_detail = State()
    confirm_buy = State()


class TradingSG(StatesGroup):
    dashboard = State()
    active_orders = State()
    order_detail = State()
    confirm_cancel = State()
    set_sell_price = State()
    confirm_sell = State()


class StrategySG(StatesGroup):
    list = State()
    create_choose = State()
    fm_multiplier = State()
    fm_min_profit = State()
    fm_max_buy = State()
    rs_min_rarity = State()
    rs_max_price_ratio = State()
    rs_target_profit = State()
    uh_value_ratio = State()
    uh_max_price = State()
    fs_below_floor = State()
    fs_daily_limit = State()
    custom_name = State()
    custom_buy_signal = State()
    custom_sell_signal = State()
    edit = State()
    confirm_delete = State()


class AnalyticsSG(StatesGroup):
    main = State()
    gainers = State()
    losers = State()
    liquidity = State()
    chart_select = State()


class PortfolioSG(StatesGroup):
    list = State()
    gift_detail = State()
    set_sell_price = State()
    confirm_sell = State()


class SettingsSG(StatesGroup):
    main = State()
    stop_loss_pct = State()
    max_buy_ton = State()
    min_profit_ton = State()
    large_deal_confirm = State()
    proxy_input = State()
    notifications = State()
    dry_run_toggle = State()
