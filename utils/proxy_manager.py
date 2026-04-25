"""Tiny proxy manager — one primary URL with optional rotation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class ProxyManager:
    """Holds primary + optional fallbacks; rotates on failures."""

    primary: str | None = None
    fallbacks: list[str] = field(default_factory=list)
    _failures: dict[str, int] = field(default_factory=dict)
    _current: str | None = None

    def __post_init__(self) -> None:
        self._current = self.primary

    @property
    def current(self) -> str | None:
        return self._current

    def all(self) -> list[str]:
        return [p for p in (self.primary, *self.fallbacks) if p]

    def report_failure(self) -> str | None:
        if not self._current:
            return None
        self._failures[self._current] = self._failures.get(self._current, 0) + 1
        if self._failures[self._current] >= 3:
            choices = [p for p in self.all() if p != self._current]
            if choices:
                self._current = random.choice(choices)
                self._failures[self._current] = 0
        return self._current

    def report_success(self) -> None:
        if self._current and self._current in self._failures:
            self._failures[self._current] = 0
