"""Validation helpers for user input."""

from __future__ import annotations

import re

from .exceptions import ValidationError

_PRICE_RE = re.compile(r"^\d+([.,]\d+)?$")


def parse_ton_amount(text: str, *, min_value: float = 0.0, max_value: float = 1_000_000.0) -> float:
    """Parse TON amount from user input. Accepts both `,` and `.` separators."""
    if text is None:
        raise ValidationError("Сумма не указана")
    cleaned = text.strip().replace(" ", "").replace(",", ".")
    if not _PRICE_RE.match(cleaned):
        raise ValidationError(f"Некорректное значение: {text!r}")
    try:
        value = float(cleaned)
    except ValueError as exc:
        raise ValidationError(f"Не удалось преобразовать: {text!r}") from exc
    if value < min_value:
        raise ValidationError(f"Значение должно быть ≥ {min_value}")
    if value > max_value:
        raise ValidationError(f"Значение должно быть ≤ {max_value}")
    return round(value, 4)


def parse_int(text: str, *, min_value: int = 0, max_value: int = 10**9) -> int:
    """Parse positive integer."""
    cleaned = text.strip()
    if not cleaned.isdigit():
        raise ValidationError(f"Ожидается целое число, получено {text!r}")
    value = int(cleaned)
    if value < min_value:
        raise ValidationError(f"Значение должно быть ≥ {min_value}")
    if value > max_value:
        raise ValidationError(f"Значение должно быть ≤ {max_value}")
    return value


def parse_pct(text: str) -> float:
    """Parse percent value 0..100."""
    return parse_ton_amount(text, min_value=0.0, max_value=100.0)


def ton_to_nano(value: float) -> int:
    """TON → nanoTON with safe rounding."""
    return int(round(value * 1_000_000_000))


def nano_to_ton(value: int) -> float:
    """nanoTON → TON."""
    return value / 1_000_000_000
