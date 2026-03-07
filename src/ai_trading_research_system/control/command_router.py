"""
Command router: map user intent (natural language / command) to internal subcommand + args.
Aligned with cli.py subcommands so that OpenClaw Agent / Skill can use the same surface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RoutedCommand:
    """Internal command after routing; same as cli subcommand + args."""
    subcommand: str  # "research" | "backtest" | "paper" | "demo"
    symbol: str = "NVDA"
    start_date: str | None = None
    end_date: str | None = None
    once: bool = False
    use_mock: bool = False
    use_llm: bool = False

    def to_kwargs(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "symbol": self.symbol,
            "use_mock": self.use_mock,
            "use_llm": self.use_llm,
        }
        if self.subcommand == "backtest":
            if self.start_date is not None:
                out["start_date"] = self.start_date
            if self.end_date is not None:
                out["end_date"] = self.end_date
        if self.subcommand == "paper":
            out["once"] = self.once
        return out


def route_intent(
    intent: str,
    *,
    default_symbol: str = "NVDA",
    use_mock: bool = False,
    use_llm: bool = False,
) -> RoutedCommand:
    """
    Map user intent to a RoutedCommand (subcommand + args).
    Intent examples: "analyse NVDA", "analyze AAPL", "run backtest", "run backtest NVDA", "show experience", "demo NVDA".
    """
    intent_lower = intent.strip().lower()
    parts = intent_lower.split()
    symbol = default_symbol
    # Try to take last token as symbol if it looks like a ticker (all caps or short)
    for i, p in enumerate(parts):
        if len(p) <= 5 and p.isalpha() and p.upper() == p:
            symbol = p.upper()
            break
        if p in ("nvda", "aapl", "msft", "tsla", "goog", "amzn", "meta"):
            symbol = p.upper()
            break

    if "analyse" in intent_lower or "analyze" in intent_lower or intent_lower.startswith("research"):
        return RoutedCommand("research", symbol=symbol, use_mock=use_mock, use_llm=use_llm)
    if "backtest" in intent_lower or "回测" in intent_lower:
        return RoutedCommand("backtest", symbol=symbol, use_mock=use_mock, use_llm=use_llm)
    if "paper" in intent_lower or "纸面" in intent_lower:
        return RoutedCommand("paper", symbol=symbol, once=True, use_mock=use_mock, use_llm=use_llm)
    if "demo" in intent_lower or "e2e" in intent_lower:
        return RoutedCommand("demo", symbol=symbol, use_mock=use_mock, use_llm=use_llm)
    if "experience" in intent_lower or "经验" in intent_lower or "show" in intent_lower and "history" in intent_lower:
        # Placeholder: no subcommand yet for experience query; map to research for now
        return RoutedCommand("research", symbol=symbol, use_mock=use_mock, use_llm=use_llm)

    # Default: treat as research with possible symbol
    return RoutedCommand("research", symbol=symbol, use_mock=use_mock, use_llm=use_llm)
