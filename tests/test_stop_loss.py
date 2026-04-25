"""Stop loss engine tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.stop_loss import StopLossAction, StopLossEngine


def test_stop_loss_triggers() -> None:
    engine = StopLossEngine(commission=0.05)
    decision = engine.evaluate(
        buy_price=10.0,
        current_floor=8.0,
        bought_at=datetime.now(UTC),
        stop_loss_pct=15.0,
    )
    assert decision.action == StopLossAction.SELL_NOW
    assert decision.sell_at >= 9.0
    assert decision.sell_at <= 10.0


def test_stop_loss_holds_when_above_threshold() -> None:
    engine = StopLossEngine(commission=0.05)
    decision = engine.evaluate(
        buy_price=10.0,
        current_floor=9.5,
        bought_at=datetime.now(UTC),
        stop_loss_pct=15.0,
    )
    assert decision.action == StopLossAction.HOLD


def test_stop_loss_consider_after_age() -> None:
    engine = StopLossEngine(commission=0.05, consider_sell_after_hours=1)
    decision = engine.evaluate(
        buy_price=10.0,
        current_floor=9.0,
        bought_at=datetime.now(UTC) - timedelta(hours=2),
        stop_loss_pct=15.0,
    )
    assert decision.action == StopLossAction.CONSIDER_SELL
