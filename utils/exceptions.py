"""Custom exception hierarchy for the bot."""

from __future__ import annotations


class MrktBotError(Exception):
    """Base class for all bot-specific errors."""


class NetworkError(MrktBotError):
    """Network-level failures (timeouts, DNS, proxy, etc.)."""


class AuthError(MrktBotError):
    """Authentication / token-related failures."""


class RateLimitError(MrktBotError):
    """API rate limit hit (HTTP 429 or equivalent)."""


class InsufficientBalanceError(MrktBotError):
    """User does not have enough TON to complete operation."""


class TradingError(MrktBotError):
    """Generic trading failure (cooldown, duplicate, etc.)."""


class ValidationError(MrktBotError):
    """User input or configuration validation failed."""


class StrategyError(MrktBotError):
    """Strategy-level error (invalid params, signal failure, …)."""
