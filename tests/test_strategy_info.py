"""Verify the human-readable strategy info catalogue is complete and valid."""

from __future__ import annotations

from strategies import STRATEGY_REGISTRY
from strategies.info import get_info, list_all, render_card


def test_each_registered_strategy_has_info() -> None:
    missing = [type_id for type_id in STRATEGY_REGISTRY if get_info(type_id) is None]
    assert not missing, f"missing info entries: {missing}"


def test_list_all_returns_at_least_registered_count() -> None:
    assert len(list_all()) >= len(STRATEGY_REGISTRY)


def test_card_includes_required_sections() -> None:
    for info in list_all():
        text = render_card(info)
        assert info.display_name in text
        assert "Риск" in text
        assert "Частота" in text
        assert "Удержание" in text
        if info.params:
            assert "Параметры" in text
        if info.examples:
            assert "Примеры" in text


def test_risk_levels_are_valid() -> None:
    valid = {"low", "medium", "high", "varies"}
    for info in list_all():
        assert info.risk_level in valid, info.type_id


def test_info_param_entries_have_doc_strings() -> None:
    """Whatever params an info card lists, each entry must be a triple of
    (key, default, doc) where key is non-empty."""
    for info in list_all():
        for entry in info.params:
            assert len(entry) == 3
            key, default, doc = entry
            assert isinstance(key, str) and key
            # default may be a value or a string repr — both fine
            assert default is not None
            assert isinstance(doc, str)
