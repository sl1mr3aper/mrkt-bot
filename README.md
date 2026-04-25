# 🏆 MRKT NFT Trading Bot

Universal, fully-automated Telegram bot for trading NFT gifts on
[tgmrkt.io](https://tgmrkt.io). Built around **aiogram 3** (UI) and the
[`amrkt`](https://pypi.org/project/amrkt/) async client (MRKT API + Pyrogram
auth).

> Все настройки управляются кнопками. Бот работает 24/7, поддерживает 7
> стратегий, dry-run, стоп-лоссы и иерархическое меню.

---

## ⚡ Quick start

```bash
git clone https://github.com/sl1mr3aper/mrkt-bot.git
cd mrkt-bot

python3.11 -m venv .venv
source .venv/bin/activate

make dev          # установить зависимости (incl. dev tools)
cp .env.example .env
$EDITOR .env      # заполнить BOT_TOKEN, MRKT_API_ID, MRKT_API_HASH, ADMIN_ID

make db-init      # создать SQLite базу
make run          # запустить бот
```

Затем открыть бота в Telegram → `/start`.

---

## 🔑 Что нужно вписать в `.env`

| Переменная       | Где взять                                            |
| ---------------- | ---------------------------------------------------- |
| `BOT_TOKEN`      | [@BotFather](https://t.me/BotFather)                 |
| `ADMIN_ID`       | ваш Telegram user id (например через @userinfobot)   |
| `MRKT_API_ID`    | https://my.telegram.org/auth → API development tools |
| `MRKT_API_HASH`  | то же самое                                          |
| `PROXY_URL`      | (опционально) `socks5://user:pass@host:1080`         |

При первом запуске Pyrogram попросит код подтверждения в Telegram — это
нормально, нужен только один раз. После этого `mrkt_session.session` будет
сохранён локально.

---

## 🏗 Архитектура

```
mrkt_bot/
├── main.py                # точка входа + graceful shutdown
├── config.py              # pydantic-settings
│
├── bot/                   # Telegram UI (aiogram 3)
│   ├── handlers/          # /start, фильтры, поиск, торговля, настройки…
│   ├── keyboards/         # inline-клавиатуры и клавиатуры-строители
│   ├── middlewares/       # auth, logging, error handler
│   └── states/            # FSM
│
├── core/                  # ядро торговой логики
│   ├── auth_manager.py    # JWT + Pyrogram авторизация
│   ├── mrkt_client.py     # обёртка над `amrkt`
│   ├── trading_engine.py  # главный цикл
│   ├── order_manager.py   # активные ордера + пересоздание
│   ├── price_analyzer.py  # fair-value / редкость / ликвидность
│   ├── strategy_runner.py # подключение стратегий
│   ├── stop_loss.py       # стоп-лоссы 24/7
│   ├── balance_tracker.py
│   ├── profit_tracker.py
│   ├── cooldown_manager.py
│   └── market_state.py    # in-memory snapshot рынка
│
├── strategies/            # 7 готовых + custom
│   ├── floor_multiplier.py
│   ├── rarity_sniper.py
│   ├── undervalue_hunter.py
│   ├── floor_sniper.py
│   ├── momentum.py
│   ├── number_hunter.py
│   └── custom.py
│
├── tasks/                 # фоновые задачи под watchdog
├── db/                    # SQLAlchemy 2.0 (aiosqlite)
├── analytics/             # rarity, charts, отчёты, ликвидность
└── utils/                 # logger, formatters, retry, rate limiter, …
```

---

## 🤖 Стратегии

| Стратегия          | Профит/сделку | Риск  | Описание                                     |
| ------------------ | ------------- | ----- | -------------------------------------------- |
| `FloorMultiplier`  | 10–25 %       | Low   | покупка по floor, продажа +X %               |
| `RaritySniper`     | 50–300 %      | Med   | редкие модели по цене common                 |
| `UndervalueHunter` | 100–500 %     | Med   | fair value / price ≥ 1.5×                    |
| `FloorSniper`      | 3–10 %        | Low   | мгновенная скупка ниже floor                 |
| `Momentum`         | 20–100 %      | High  | хайп-трейдинг с trailing stop                |
| `NumberHunter`     | переменно     | Med   | низкие номера #1–#999                        |
| `Custom`           | —             | —     | пользовательские правила                     |

DRY-RUN включён по умолчанию. Чтобы переключить — `Настройки → DRY RUN`.

---

## 🧪 Tests / lint

```bash
make lint        # ruff
make typecheck   # mypy
make test        # pytest
make test-cov    # с покрытием
```

CI запускает все три проверки на каждый PR.

---

## ⚠️ Disclaimer

Софт предоставляется «как есть». Рынок NFT-подарков высоко волатильный,
никаких гарантий прибыли нет. По умолчанию активирован DRY-RUN — изучите
поведение бота на симуляции прежде чем включать реальные сделки.
