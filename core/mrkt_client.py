"""High-level MRKT client built on top of `amrkt`.

Adds:
  * a unified async API used by the rest of the bot,
  * a `MockMrktClient` shim used in unit tests / dry-run only setups,
  * a `normalize_gift` helper that turns any incoming gift into a plain dict.

We deliberately keep this layer thin — heavy lifting belongs to ``amrkt``.
"""

from __future__ import annotations

from typing import Any

from core.demo_dataset import (
    BACKDROPS as _DEMO_BACKDROPS,
)
from core.demo_dataset import (
    SYMBOLS as _DEMO_SYMBOLS,
)
from core.demo_dataset import (
    make_collections as _demo_collections,
)
from core.demo_dataset import (
    make_listings as _demo_listings,
)
from core.demo_dataset import (
    make_models_index as _demo_models_index,
)
from utils.exceptions import (
    AuthError,
    InsufficientBalanceError,
    NetworkError,
    RateLimitError,
)
from utils.logger import get_logger
from utils.rate_limiter import RateLimiter
from utils.validators import nano_to_ton, ton_to_nano

log = get_logger(__name__)


def normalize_gift(gift: Any) -> dict[str, Any]:
    """Convert an `amrkt.Gift` (or dict) into a plain dict consumed elsewhere."""
    if isinstance(gift, dict):
        d = dict(gift)
    else:
        d = {}
        for attr in dir(gift):
            if attr.startswith("_"):
                continue
            try:
                value = getattr(gift, attr)
            except Exception:
                continue
            if callable(value):
                continue
            d[attr] = value

    out: dict[str, Any] = {
        "id": d.get("id"),
        "name": d.get("name") or d.get("title"),
        "title": d.get("title"),
        "number": d.get("number"),
        "collection": d.get("collection_name") or d.get("collectionName"),
        "collection_title": d.get("collection_title") or d.get("collectionTitle"),
        "model": d.get("model_name") or d.get("modelName"),
        "backdrop": d.get("backdrop_name") or d.get("backdropName"),
        "symbol": d.get("symbol_name") or d.get("symbolName"),
        "model_rarity_per_mille": d.get("model_rarity_per_mille") or d.get("modelRarityPerMille"),
        "backdrop_rarity_per_mille": d.get("backdrop_rarity_per_mille") or d.get("backdropRarityPerMille"),
        "symbol_rarity_per_mille": d.get("symbol_rarity_per_mille") or d.get("symbolRarityPerMille"),
        "is_on_sale": d.get("is_on_sale") if "is_on_sale" in d else d.get("isOnSale"),
        "is_mine": d.get("is_mine") if "is_mine" in d else d.get("isMine"),
        "minted": d.get("minted"),
        "mintable": d.get("mintable"),
    }

    # rarity per mille → percent (1 promille = 0.1%)
    for key in ("model", "backdrop", "symbol"):
        per_mille = out.pop(f"{key}_rarity_per_mille", None)
        if per_mille is not None:
            try:
                out[f"{key}Rarity"] = float(per_mille) / 10.0
            except (TypeError, ValueError):
                out[f"{key}Rarity"] = 50.0

    # price in TON
    sale_price_nano = d.get("sale_price") or d.get("salePrice")
    if sale_price_nano is not None:
        try:
            out["price"] = nano_to_ton(int(sale_price_nano))
            out["price_nano"] = int(sale_price_nano)
        except (TypeError, ValueError):
            pass

    floor_nano = (
        d.get("floor_price_by_collection")
        or d.get("floorPriceNanoTONsByCollection")
    )
    if floor_nano is not None:
        try:
            out["floor_price"] = nano_to_ton(int(floor_nano))
        except (TypeError, ValueError):
            pass

    return out


class MrktClient:
    """Thin async wrapper over `amrkt.MarketClient` adding rate limiting + retries."""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        *,
        session_name: str = "mrkt_session",
        workdir: str = ".",
        proxy: str | None = None,
        proxy_api_only: bool = True,
        impersonate: str = "chrome124",
        rate: int = 30,
        per: float = 60.0,
    ) -> None:
        try:
            # Imported lazily so that unit tests / dry-run installs that
            # don't have Pyrogram still work via MockMrktClient.
            from amrkt import MarketClient
        except Exception as exc:  # pragma: no cover - depends on environment
            raise ImportError(
                "amrkt package not installed; run `pip install amrkt`"
            ) from exc

        self._inner = MarketClient(
            api_id=api_id,
            api_hash=api_hash,
            session_name=session_name,
            workdir=workdir,
            proxy=proxy,
            proxy_api_only=proxy_api_only,
            impersonate=impersonate,
        )
        self.rate_limiter = RateLimiter(rate=rate, per=per)

    # ─── auth ──────────────────────────────────────────────

    async def ensure_auth(self) -> None:
        try:
            await self._inner._ensure_authenticated()  # type: ignore[attr-defined]
        except Exception as exc:
            raise AuthError(str(exc)) from exc

    async def force_refresh(self) -> None:
        try:
            self._inner._token = await self._inner._get_new_token()  # type: ignore[attr-defined]
        except Exception as exc:
            raise AuthError(f"Failed to refresh JWT: {exc}") from exc

    async def close(self) -> None:
        try:
            await self._inner.__aexit__(None, None, None)
        except Exception:
            pass

    # ─── balance ──────────────────────────────────────────

    async def get_balance_ton(self) -> float:
        await self.rate_limiter.acquire()
        try:
            balance = await self._inner.get_balance()
        except Exception as exc:
            raise self._wrap(exc)
        return float(balance.hard_ton + balance.soft_ton)

    # ─── collections / search ─────────────────────────────

    async def list_collections(self) -> list[dict[str, Any]]:
        await self.rate_limiter.acquire()
        try:
            collections = await self._inner.get_collections()
        except Exception as exc:
            raise self._wrap(exc)
        return [
            {
                "name": c.name,
                "title": c.title,
                "floor_price": c.floor_price_ton,
                "volume": c.volume,
                "is_new": c.is_new,
                "previous_floor": (
                    (c.previous_day_floor_price_nano_tons or 0) / 1_000_000_000
                    if c.previous_day_floor_price_nano_tons
                    else None
                ),
            }
            for c in collections
        ]

    async def search_gifts(
        self,
        *,
        collection_names: list[str] | None = None,
        model_names: list[str] | None = None,
        backdrop_names: list[str] | None = None,
        symbol_names: list[str] | None = None,
        ordering: str = "Price",
        low_to_high: bool = True,
        min_price_ton: float | None = None,
        max_price_ton: float | None = None,
        mintable: bool | None = None,
        number: int | None = None,
        count: int = 20,
        cursor: str = "",
    ) -> dict[str, Any]:
        await self.rate_limiter.acquire()
        try:
            result = await self._inner.search_gifts(
                collection_names=collection_names or [],
                model_names=model_names or [],
                backdrop_names=backdrop_names or [],
                symbol_names=symbol_names or [],
                ordering=ordering,
                low_to_high=low_to_high,
                min_price=ton_to_nano(min_price_ton) if min_price_ton else None,
                max_price=ton_to_nano(max_price_ton) if max_price_ton else None,
                mintable=mintable,
                number=number,
                count=count,
                cursor=cursor,
            )
        except Exception as exc:
            raise self._wrap(exc)
        return {
            "items": [normalize_gift(g) for g in result.items],
            "total": result.total,
            "cursor": result.cursor,
        }

    async def list_models(
        self, collection_names: list[str] | None = None
    ) -> list[str]:
        """Best-effort attribute discovery via a search sample.

        amrkt does not expose a dedicated attributes endpoint, so we sample
        the most recent listings and extract distinct model names.
        """
        try:
            page = await self.search_gifts(
                collection_names=collection_names or None,
                count=100,
            )
        except Exception:
            return []
        return sorted({(g.get("model") or "") for g in page["items"] if g.get("model")})

    async def list_backdrops(self) -> list[str]:
        try:
            page = await self.search_gifts(count=100)
        except Exception:
            return []
        return sorted({(g.get("backdrop") or "") for g in page["items"] if g.get("backdrop")})

    async def list_symbols(self) -> list[str]:
        try:
            page = await self.search_gifts(count=100)
        except Exception:
            return []
        return sorted({(g.get("symbol") or "") for g in page["items"] if g.get("symbol")})

    # ─── inventory ────────────────────────────────────────

    async def get_inventory(self, *, count: int = 100) -> list[dict[str, Any]]:
        await self.rate_limiter.acquire()
        try:
            result = await self._inner.get_inventory(count=count)
        except Exception as exc:
            raise self._wrap(exc)
        return [normalize_gift(g) for g in result.items]

    # ─── trading ──────────────────────────────────────────

    async def buy(self, gift_ids: list[str]) -> list[dict[str, Any]]:
        await self.rate_limiter.acquire()
        try:
            results = await self._inner.buy_gifts(gift_ids)
        except Exception as exc:
            raise self._wrap(exc)
        return [
            {
                "price_ton": r.price_ton,
                "gift": normalize_gift(r.user_gift) if r.user_gift else None,
            }
            for r in results
        ]

    async def list_for_sale(
        self, gift_ids: list[str], prices_ton: list[float]
    ) -> dict[str, Any]:
        await self.rate_limiter.acquire()
        prices_nano = [ton_to_nano(p) for p in prices_ton]
        try:
            result = await self._inner.sell_gifts(gift_ids, prices_nano)
        except Exception as exc:
            raise self._wrap(exc)
        return {"ids": result.ids, "prices_ton": result.prices_ton}

    async def cancel_sale(self, gift_ids: list[str]) -> list[str]:
        await self.rate_limiter.acquire()
        try:
            return await self._inner.cancel_sale(gift_ids)
        except Exception as exc:
            raise self._wrap(exc)

    async def change_price(
        self, gift_ids: list[str], prices_ton: list[float]
    ) -> dict[str, Any]:
        await self.rate_limiter.acquire()
        prices_nano = [ton_to_nano(p) for p in prices_ton]
        try:
            result = await self._inner.change_price(gift_ids, prices_nano)
        except Exception as exc:
            raise self._wrap(exc)
        return {"ids": result.ids, "prices_ton": result.prices_ton}

    async def get_activities(
        self, *, offset: int = 0, count: int = 50, is_active: bool = True
    ) -> list[Any]:
        await self.rate_limiter.acquire()
        try:
            return await self._inner.get_activities(
                offset=offset, count=count, is_active=is_active
            )
        except Exception as exc:
            raise self._wrap(exc)

    # ─── error mapping ────────────────────────────────────

    @staticmethod
    def _wrap(exc: Exception) -> Exception:
        msg = str(exc).lower()
        if "401" in msg or "authentication" in msg:
            return AuthError(str(exc))
        if "429" in msg or "rate" in msg:
            return RateLimitError(str(exc))
        if "balance" in msg or "insufficient" in msg:
            return InsufficientBalanceError(str(exc))
        if "timed out" in msg or "timeout" in msg or "connection" in msg or "network" in msg:
            return NetworkError(str(exc))
        return exc


class MockMrktClient:
    """Static stand-in used by tests / first-run setup with no credentials.

    Seeded with synthetic data covering 4 collections, 16 models, 8 backdrops,
    8 symbols and ~40 listings so the bot UI can be exercised without real
    MRKT credentials.
    """

    def __init__(self, *, seed_demo: bool = True) -> None:
        self.rate_limiter = RateLimiter(rate=1000, per=1.0)
        self._balance = 250.0
        self.collections: list[dict[str, Any]] = (
            _demo_collections() if seed_demo else []
        )
        self.gifts: list[dict[str, Any]] = (
            _demo_listings() if seed_demo else []
        )
        self.models_by_collection: dict[str, list[str]] = (
            _demo_models_index() if seed_demo else {}
        )
        self.backdrops: list[str] = list(_DEMO_BACKDROPS) if seed_demo else []
        self.symbols: list[str] = list(_DEMO_SYMBOLS) if seed_demo else []
        self.bought_calls: list[list[str]] = []
        self.sold_calls: list[tuple[list[str], list[float]]] = []

    async def ensure_auth(self) -> None:
        return None

    async def force_refresh(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def get_balance_ton(self) -> float:
        return self._balance

    async def list_collections(self) -> list[dict[str, Any]]:
        return list(self.collections)

    async def list_models(self, collection_names: list[str] | None = None) -> list[str]:
        if not collection_names:
            out: set[str] = set()
            for v in self.models_by_collection.values():
                out.update(v)
            return sorted(out)
        out = set()
        for name in collection_names:
            out.update(self.models_by_collection.get(name, []))
        return sorted(out)

    async def list_backdrops(self) -> list[str]:
        return list(self.backdrops)

    async def list_symbols(self) -> list[str]:
        return list(self.symbols)

    async def search_gifts(
        self,
        *,
        collection_names: list[str] | None = None,
        model_names: list[str] | None = None,
        backdrop_names: list[str] | None = None,
        symbol_names: list[str] | None = None,
        ordering: str = "Price",
        low_to_high: bool = True,
        min_price_ton: float | None = None,
        max_price_ton: float | None = None,
        mintable: bool | None = None,
        number: int | None = None,
        count: int = 20,
        cursor: str = "",
    ) -> dict[str, Any]:
        items = [g for g in self.gifts if g.get("is_on_sale")]
        if collection_names:
            items = [g for g in items if g.get("collection") in collection_names]
        if model_names:
            items = [g for g in items if g.get("model") in model_names]
        if backdrop_names:
            items = [g for g in items if g.get("backdrop") in backdrop_names]
        if symbol_names:
            items = [g for g in items if g.get("symbol") in symbol_names]
        if min_price_ton is not None:
            items = [g for g in items if (g.get("price") or 0) >= min_price_ton]
        if max_price_ton is not None:
            items = [g for g in items if (g.get("price") or 0) <= max_price_ton]
        if mintable is not None:
            items = [g for g in items if bool(g.get("mintable")) == bool(mintable)]
        if number is not None:
            items = [g for g in items if g.get("number") == number]

        reverse = not low_to_high
        if ordering == "Price":
            items.sort(key=lambda g: g.get("price") or 0, reverse=reverse)
        elif ordering == "Rarity":
            items.sort(
                key=lambda g: (g.get("modelRarity") or 99) + (g.get("backdropRarity") or 99),
                reverse=reverse,
            )
        elif ordering == "Number":
            items.sort(key=lambda g: g.get("number") or 0, reverse=reverse)

        # cursor-based pagination
        start = int(cursor) if cursor.isdigit() else 0
        page = items[start:start + count]
        next_cursor = str(start + count) if start + count < len(items) else ""
        return {"items": page, "total": len(items), "cursor": next_cursor}

    async def get_inventory(self, *, count: int = 100) -> list[dict[str, Any]]:
        return [g for g in self.gifts if g.get("is_mine")]

    async def buy(self, gift_ids: list[str]) -> list[dict[str, Any]]:
        self.bought_calls.append(gift_ids)
        out = []
        for gid in gift_ids:
            for g in self.gifts:
                if g.get("id") == gid:
                    self._balance -= g.get("price", 0.0)
                    g["is_mine"] = True
                    g["is_on_sale"] = False
                    out.append({"price_ton": g.get("price", 0.0), "gift": g})
        return out

    async def list_for_sale(
        self, gift_ids: list[str], prices_ton: list[float]
    ) -> dict[str, Any]:
        self.sold_calls.append((gift_ids, prices_ton))
        for gid, p in zip(gift_ids, prices_ton, strict=False):
            for g in self.gifts:
                if g.get("id") == gid:
                    g["is_on_sale"] = True
                    g["price"] = p
        return {"ids": gift_ids, "prices_ton": prices_ton}

    async def cancel_sale(self, gift_ids: list[str]) -> list[str]:
        return list(gift_ids)

    async def change_price(
        self, gift_ids: list[str], prices_ton: list[float]
    ) -> dict[str, Any]:
        return {"ids": gift_ids, "prices_ton": prices_ton}

    async def get_activities(self, **kwargs: Any) -> list[Any]:
        return []
