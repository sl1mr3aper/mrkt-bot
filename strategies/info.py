"""Long-form descriptions and parameter docs for each strategy.

Surfaced in the bot UI so users can understand what each strategy does
before activating it. Uses a single source of truth keyed by ``type_id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StrategyInfo:
    type_id: str
    display_name: str
    short: str
    long: str
    risk_level: str  # "low" | "medium" | "high"
    expected_freq: str  # human description ("несколько сделок в час", ...)
    typical_holding: str
    params: list[tuple[str, str, str]] = field(default_factory=list)  # (key, default, doc)
    examples: list[str] = field(default_factory=list)


_DB: dict[str, StrategyInfo] = {
    "FloorMultiplier": StrategyInfo(
        type_id="FloorMultiplier",
        display_name="FloorMultiplier",
        short="Стабильный доход с floor: купил по low — продал +10–25%.",
        long=(
            "Покупает листинги, у которых цена ≤ <code>floor × buy_multiplier</code>. "
            "Цель продажи — <code>floor × sell_multiplier</code> с учётом комиссии. "
            "Подходит для ликвидных коллекций с хорошим стаканом, "
            "где спред между floor и 2-й самой дешёвой позицией &lt; 10%."
        ),
        risk_level="low",
        expected_freq="до 30 сделок в день на ликвидных коллекциях",
        typical_holding="минуты — несколько часов",
        params=[
            ("buy_multiplier", "1.00", "максимум, который согласны платить от floor (1.00 = ровно floor)"),
            ("sell_multiplier", "1.15", "цель продажи относительно floor (+15%)"),
            ("min_profit_ton", "0.05 TON", "минимально допустимая чистая прибыль с одной сделки"),
            ("max_position_ton", "10 TON", "верхний потолок цены за один лот"),
            ("max_positions", "5", "максимум одновременных открытых позиций"),
        ],
        examples=[
            "Floor = 1.20 TON, sale_price = 1.18 TON → buy. Продаём по 1.38 TON.",
            "Floor = 4.00 TON, sale_price = 4.10 TON → ❌ skip (выше buy_multiplier).",
        ],
    ),
    "RaritySniper": StrategyInfo(
        type_id="RaritySniper",
        display_name="RaritySniper",
        short="Охотник за редкостями (Legendary/Epic) — продажа по справедливой стоимости.",
        long=(
            "Покупает только листинги с rarity_score ≥ заданного (по умолчанию 7) "
            "если их цена ≤ fair_value × discount. Fair value считается по формуле "
            "из rarity calculator (модель 55%, фон 30%, символ 15%) и floor коллекции."
        ),
        risk_level="medium",
        expected_freq="1–10 сделок в день",
        typical_holding="часы — сутки",
        params=[
            ("min_rarity", "7.0", "минимальный composite rarity (0–10)"),
            ("max_discount", "0.7", "цена ≤ fair × max_discount → buy"),
            ("min_profit_ton", "0.5 TON", "минимально допустимая прибыль"),
            ("max_position_ton", "20 TON", "потолок цены лота"),
        ],
        examples=[
            "Rarity 8.4, fair_value 6.0 TON, sale_price 3.8 TON → buy.",
            "Rarity 9.1, fair_value 12 TON, sale_price 11 TON → ❌ skip (≥ 0.7×fair).",
        ],
    ),
    "UndervalueHunter": StrategyInfo(
        type_id="UndervalueHunter",
        display_name="UndervalueHunter",
        short="Поиск недооценённых: цена &lt; справедливая на ≥30%.",
        long=(
            "Использует только справедливую стоимость без сравнения с floor. "
            "Покупает, если sale_price &lt; fair_value × (1 − discount). "
            "Чаще всего ловит листинги, ошибочно выставленные дешевле рынка."
        ),
        risk_level="medium",
        expected_freq="несколько сделок в час во время волатильности",
        typical_holding="часы",
        params=[
            ("discount", "0.30", "цена ≤ fair_value × (1 − discount) — триггер"),
            ("min_profit_ton", "0.3 TON", ""),
            ("max_position_ton", "15 TON", ""),
        ],
    ),
    "FloorSniper": StrategyInfo(
        type_id="FloorSniper",
        display_name="FloorSniper",
        short="Очень быстрая ловля резких просадок floor (флэш-краш).",
        long=(
            "Реагирует, когда сейчас на маркете появилась цена &lt; previous_floor × drop. "
            "Подходит для коллекций с высокой волатильностью (PlushPepe, Astral Shard). "
            "Требует низкой задержки сети и высокого rate-limit."
        ),
        risk_level="high",
        expected_freq="1–5 в час",
        typical_holding="минуты",
        params=[
            ("drop_pct", "10.0", "минимальная просадка от пред. floor (%)"),
            ("min_profit_ton", "0.4 TON", ""),
            ("max_position_ton", "8 TON", ""),
        ],
    ),
    "Momentum": StrategyInfo(
        type_id="Momentum",
        display_name="Momentum",
        short="Покупка коллекций на росте: floor вырос ≥ 5% за 1ч.",
        long=(
            "Анализирует историю price_history (последние 1–6 часов). "
            "Если floor растёт устойчиво → ищет листинги ≤ текущего floor "
            "и продаёт по новому, более высокому floor."
        ),
        risk_level="medium",
        expected_freq="1–8 сделок в день",
        typical_holding="часы",
        params=[
            ("growth_pct_1h", "5.0", "минимальный рост floor за час"),
            ("growth_pct_6h", "12.0", "минимальный рост за 6ч"),
            ("max_position_ton", "12 TON", ""),
        ],
    ),
    "NumberHunter": StrategyInfo(
        type_id="NumberHunter",
        display_name="NumberHunter",
        short="Сбор красивых номеров: 1, 7, 77, 100, 777, 1000, ...",
        long=(
            "Покупает листинги, у которых number ∈ заданном множестве. "
            "Цена ≤ floor × multiplier. Хорошо работает на коллекциях с высокой "
            "перепродажей по 'сильным' номерам (777, 100, 1)."
        ),
        risk_level="low",
        expected_freq="редкие, 1–5 в день",
        typical_holding="дни",
        params=[
            ("numbers", "[1,7,77,100,777,1000]", "целевые номера"),
            ("multiplier", "2.0", "максимум floor × multiplier"),
            ("max_position_ton", "8 TON", ""),
        ],
    ),
    "Custom": StrategyInfo(
        type_id="Custom",
        display_name="Custom",
        short="Свой набор условий: цена/редкость/коллекция/номер/sell_multiplier.",
        long=(
            "Пользовательская стратегия — указываешь любую комбинацию: "
            "минимальный rarity, max_price, конкретные коллекции/модели/символы, "
            "целевую sell_multiplier. Используется как песочница."
        ),
        risk_level="varies",
        expected_freq="зависит от настроек",
        typical_holding="зависит",
        params=[
            ("max_price_ton", "—", "верхний потолок цены"),
            ("min_rarity", "0", "минимальная редкость (0..10)"),
            ("collection_names", "[]", "ограничить набором коллекций"),
            ("sell_multiplier", "1.20", "цель продажи относительно buy_price"),
        ],
    ),
    "Arbitrage": StrategyInfo(
        type_id="Arbitrage",
        display_name="Arbitrage",
        short="Сравнение цен между моделями одной коллекции.",
        long=(
            "Если внутри коллекции одна модель котируется значительно дешевле "
            "других (≥ 25%) — покупает её и выставляет по медиане модели. "
            "Эффективна на узких рынках с малым числом продавцов."
        ),
        risk_level="medium",
        expected_freq="несколько в день",
        typical_holding="часы",
        params=[
            ("min_spread_pct", "25.0", "разница в %"),
            ("min_profit_ton", "0.4 TON", ""),
        ],
    ),
    "MeanReversion": StrategyInfo(
        type_id="MeanReversion",
        display_name="MeanReversion",
        short="Возврат к средней: покупка при отклонении floor от 7д-средней.",
        long=(
            "Считает среднюю и стд. отклонение floor за 7 дней. Если текущий floor "
            "&lt; mean − std → покупка, продажа при возврате к mean."
        ),
        risk_level="medium",
        expected_freq="1–3 в день",
        typical_holding="дни",
        params=[
            ("window_days", "7", "окно для расчёта средней"),
            ("k_std", "1.0", "сколько std вниз — триггер"),
        ],
    ),
    "ScalperPro": StrategyInfo(
        type_id="ScalperPro",
        display_name="ScalperPro",
        short="Скальпинг с микрозазорами 2–5%, сверхвысокая частота.",
        long=(
            "Очень короткие позиции на ликвидных коллекциях. "
            "Использует bid-ask анализ (cluster_size_at_floor, spread_pct). "
            "Рекомендуется только при стабильном rate-limit и low-latency прокси."
        ),
        risk_level="high",
        expected_freq="≥ 50 сделок в день",
        typical_holding="секунды — минуты",
        params=[
            ("micro_spread_pct", "3.0", "минимальный спред цели"),
            ("min_cluster", "5", "минимум листингов в кластере у floor"),
        ],
    ),
}


def get_info(type_id: str) -> StrategyInfo | None:
    return _DB.get(type_id)


def list_all() -> list[StrategyInfo]:
    return list(_DB.values())


def render_card(info: StrategyInfo) -> str:
    lines = [
        f"🤖 <b>{info.display_name}</b>",
        f"<i>{info.short}</i>",
        "",
        info.long,
        "",
        f"📊 Риск: <b>{info.risk_level}</b>",
        f"⏱ Частота: {info.expected_freq}",
        f"🕐 Удержание: {info.typical_holding}",
    ]
    if info.params:
        lines.append("")
        lines.append("<b>Параметры:</b>")
        for key, default, doc in info.params:
            extra = f" — <i>{doc}</i>" if doc else ""
            lines.append(f"• <code>{key}</code> = <code>{default}</code>{extra}")
    if info.examples:
        lines.append("")
        lines.append("<b>Примеры:</b>")
        for ex in info.examples:
            lines.append(f"• {ex}")
    return "\n".join(lines)
