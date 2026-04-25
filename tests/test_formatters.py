"""Formatters / validators sanity checks."""

from __future__ import annotations

import pytest

from utils.formatters import fmt_pct, fmt_rarity, fmt_ton, rarity_label
from utils.validators import nano_to_ton, parse_pct, parse_ton_amount, ton_to_nano


def test_fmt_ton() -> None:
    assert fmt_ton(1.234) == "1.23 TON"
    assert fmt_ton(-0.5, sign=True) == "-0.50 TON"
    assert fmt_ton(None) == "—"


def test_fmt_pct() -> None:
    assert fmt_pct(15.5).startswith("+15.5")
    assert fmt_pct(-3.0, decimals=2).startswith("-3.00")


def test_fmt_rarity() -> None:
    assert "Legendary" in fmt_rarity(9.7)
    assert "Common" in fmt_rarity(2.0)


def test_rarity_label_boundaries() -> None:
    assert rarity_label(9.5) == "Legendary"
    assert rarity_label(7.0) == "Rare"
    assert rarity_label(0.0) == "Common"


def test_parse_ton() -> None:
    assert parse_ton_amount("1.5") == 1.5
    assert parse_ton_amount("1,5") == 1.5


def test_parse_ton_invalid() -> None:
    with pytest.raises(Exception):
        parse_ton_amount("abc")


def test_parse_pct_bounds() -> None:
    with pytest.raises(Exception):
        parse_pct("150")


def test_ton_nano_roundtrip() -> None:
    assert nano_to_ton(ton_to_nano(2.5)) == 2.5
