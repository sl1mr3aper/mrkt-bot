"""Tiny TTL-cache implementation used by the bot to avoid hammering MRKT.

Two flavours:

* :class:`TTLCache` — a regular ``dict``-style cache where each entry has its
  own TTL (or a shared default).
* :class:`AsyncMemoize` — a decorator that caches the result of an async
  function call for ``ttl`` seconds, keyed by ``(args, frozenset(kwargs))``.

Both are intentionally very small (no LRU eviction yet — the bot's working set
is tiny) but cover the most common use cases:

>>> cache = TTLCache(default_ttl=60)
>>> cache.set("floor:PlushPepe", 1.85)
>>> cache.get("floor:PlushPepe")
1.85
"""

from __future__ import annotations

import asyncio
import functools
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class TTLCache(Generic[T]):
    def __init__(self, *, default_ttl: float = 60.0) -> None:
        self._default_ttl = default_ttl
        self._data: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < monotonic():
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: T, *, ttl: float | None = None) -> None:
        ttl_v = self._default_ttl if ttl is None else ttl
        self._data[key] = (monotonic() + ttl_v, value)

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None

    def __len__(self) -> int:
        return sum(1 for k, (exp, _) in self._data.items() if exp >= monotonic())


class AsyncMemoize:
    """Decorator: cache an async function's result for ``ttl`` seconds.

    Usage::

        @AsyncMemoize(ttl=30)
        async def fetch_floor(name: str) -> float:
            return await client.fetch_floor(name)
    """

    def __init__(self, ttl: float = 30.0) -> None:
        self._ttl = ttl
        self._cache: TTLCache[Any] = TTLCache(default_ttl=ttl)
        self._lock = asyncio.Lock()

    def __call__(self, fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapped(*args: Any, **kwargs: Any) -> T:
            key = self._key(fn, args, kwargs)
            cached = self._cache.get(key)
            if cached is not None:
                return cached
            async with self._lock:
                cached = self._cache.get(key)
                if cached is not None:
                    return cached
                value = await fn(*args, **kwargs)
                self._cache.set(key, value)
                return value

        return wrapped

    @staticmethod
    def _key(fn: Callable, args: tuple, kwargs: dict) -> str:
        return (
            f"{fn.__module__}.{fn.__qualname__}|{args!r}|{tuple(sorted(kwargs.items()))!r}"
        )
