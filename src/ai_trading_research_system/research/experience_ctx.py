"""
ExperienceInjector: provides past experience context for Research (stub in week one).
"""
from __future__ import annotations


class ExperienceInjector:
    """
    Interface for injecting experience-derived context into Research.
    get_context(symbol) -> str: text summary of past runs/backtests for symbol (or regime).
    """

    def get_context(self, symbol: str) -> str:
        """Return experience context for symbol. Stub: returns empty string."""
        return ""
