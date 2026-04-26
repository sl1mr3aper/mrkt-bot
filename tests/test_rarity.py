"""Rarity calculator tests."""

from __future__ import annotations

import pytest

from analytics.rarity_calculator import RarityCalculator


def test_pct_to_score_legendary() -> None:
    assert RarityCalculator._pct_to_score(0.05) == 10.0
    assert RarityCalculator._pct_to_score(0.5) == 9.5
    assert RarityCalculator._pct_to_score(1.0) == 9.0


def test_pct_to_score_common() -> None:
    assert RarityCalculator._pct_to_score(50.0) == 1.0
    assert RarityCalculator._pct_to_score(20.0) == 4.0
    assert RarityCalculator._pct_to_score(5.0) == 7.0


@pytest.mark.parametrize(
    "number, expected",
    [
        (1, 1.5),
        (10, 1.5),
        (50, 1.0),
        (100, 0.7),
        (500, 0.4),
        (999, 0.2),
        (1000, 0.0),
        (None, 0.0),
    ],
)
def test_number_bonus(number: int | None, expected: float) -> None:
    assert RarityCalculator.number_bonus(number) == expected


def test_calculate_score_combines_traits() -> None:
    rc = RarityCalculator()
    score = rc.calculate_score({
        "modelRarity": 1.0,        # 9.0
        "backdropRarity": 5.0,     # 7.0
        "symbolRarity": 20.0,      # 4.0
        "number": 5,               # +1.5
    })
    expected = 9.0 * 0.55 + 7.0 * 0.30 + 4.0 * 0.15 + 1.5
    assert pytest.approx(score, rel=0.01) == round(expected, 2)


def test_estimate_fair_value_uses_multiplier() -> None:
    rc = RarityCalculator()
    fair = rc.estimate_fair_value(
        {"modelRarity": 0.05, "backdropRarity": 0.05, "symbolRarity": 0.05},
        floor_price=10.0,
    )
    # legendary band → 8x floor
    assert fair == pytest.approx(80.0, rel=0.01)
