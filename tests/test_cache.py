"""Tests for the TTL cache and async memoize decorator."""

from __future__ import annotations

import asyncio
import time

import pytest

from utils.cache import AsyncMemoize, TTLCache


def test_ttl_cache_hit_and_miss() -> None:
    cache: TTLCache[int] = TTLCache(default_ttl=10)
    cache.set("k", 42)
    assert cache.get("k") == 42
    assert cache.get("missing") is None


def test_ttl_expiration() -> None:
    cache: TTLCache[str] = TTLCache(default_ttl=0.05)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    time.sleep(0.06)
    assert cache.get("k") is None


def test_explicit_ttl_overrides_default() -> None:
    cache: TTLCache[str] = TTLCache(default_ttl=10)
    cache.set("short", "v", ttl=0.05)
    cache.set("long", "v", ttl=10)
    time.sleep(0.06)
    assert cache.get("short") is None
    assert cache.get("long") == "v"


def test_delete_and_clear() -> None:
    cache: TTLCache[int] = TTLCache(default_ttl=10)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.delete("a")
    assert cache.get("a") is None
    cache.clear()
    assert cache.get("b") is None


def test_contains_and_len() -> None:
    cache: TTLCache[int] = TTLCache(default_ttl=1.0)
    cache.set("x", 1)
    cache.set("y", 2)
    assert "x" in cache
    assert len(cache) == 2


@pytest.mark.asyncio
async def test_async_memoize_caches_within_ttl() -> None:
    calls = {"n": 0}

    @AsyncMemoize(ttl=5)
    async def fetch(name: str) -> str:
        calls["n"] += 1
        return f"result-{name}"

    assert await fetch("foo") == "result-foo"
    assert await fetch("foo") == "result-foo"
    assert calls["n"] == 1
    # Different argument → cache miss
    assert await fetch("bar") == "result-bar"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_async_memoize_ttl_expires() -> None:
    calls = {"n": 0}

    @AsyncMemoize(ttl=0.05)
    async def fetch(x: int) -> int:
        calls["n"] += 1
        return x * 2

    assert await fetch(7) == 14
    await asyncio.sleep(0.06)
    assert await fetch(7) == 14
    assert calls["n"] == 2  # cache expired, called again
