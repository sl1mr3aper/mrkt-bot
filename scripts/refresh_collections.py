"""Regenerate ``core/_real_collections_data.py`` from gifts.supply.

This is the *only* way to refresh the bot's collection catalogue without a
MRKT JWT. ``gifts.supply`` exposes a public REST API that mirrors the on-chain
state of every Telegram Gift collection. We snapshot it into a Python module
so the bot can boot offline.

Usage::

    python scripts/refresh_collections.py

The output file is committed to the repo so production deploys do not depend
on gifts.supply being reachable.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

API_URL = "https://gifts.supply/api/v1/catalog/collections?limit=500"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "core" / "_real_collections_data.py"


def fetch_collections() -> list[dict]:
    req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0 (mrkt-bot refresh)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    return data["items"]


def render_module(items: list[dict]) -> str:
    backdrops: set[str] = set()
    symbols: set[str] = set()
    rows: list[dict] = []
    for it in items:
        preview = it.get("preview") or {}
        bd = (preview.get("backdrop") or {}).get("name")
        sym = (preview.get("symbol") or {}).get("name")
        if bd:
            backdrops.add(bd)
        if sym:
            symbols.add(sym)
        models = [m.get("name") for m in (preview.get("models") or []) if m.get("name")]
        floor = float(it["floor_price"]) if it.get("floor_price") else 1.0
        rows.append(
            {
                "slug": it["slug"],
                "name": it["name"],
                "floor": floor,
                "supply": it.get("supply") or 0,
                "models_count": it.get("models_count") or 0,
                "backdrops_count": it.get("backdrops_count") or 0,
                "symbols_count": it.get("symbols_count") or 0,
                "listed_count": it.get("listed_count") or 0,
                "preview_models": models,
                "preview_backdrop": bd,
                "preview_symbol": sym,
                "theme": it.get("theme") or "",
            }
        )
    rows.sort(key=lambda x: -(x["listed_count"] or 0))

    parts: list[str] = []
    parts.append('"""Auto-generated from the gifts.supply public catalog API.\n')
    parts.append("DO NOT EDIT BY HAND. Run scripts/refresh_collections.py to regenerate.\n")
    parts.append('"""\n')
    parts.append("from __future__ import annotations\n\n")
    parts.append(f"BACKDROPS: list[str] = {sorted(backdrops)!r}\n\n")
    parts.append(f"SYMBOLS: list[str] = {sorted(symbols)!r}\n\n")
    parts.append("COLLECTIONS: list[dict] = [\n")
    for r in rows:
        parts.append("    {\n")
        for key, val in r.items():
            parts.append(f"        {key!r}: {val!r},\n")
        parts.append("    },\n")
    parts.append("]\n")
    return "".join(parts)


def main() -> int:
    items = fetch_collections()
    text = render_module(items)
    OUTPUT_PATH.write_text(text, encoding="utf-8")
    sys.stdout.write(f"Wrote {len(items)} collections to {OUTPUT_PATH}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
