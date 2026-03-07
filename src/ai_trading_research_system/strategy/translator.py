"""
Contract-to-signal translation; logic aligned with decision/rules.py.
Output is a simple signal structure for AISignalStrategy config.
"""
from __future__ import annotations

from dataclasses import dataclass

from ai_trading_research_system.research.schemas import DecisionContract


@dataclass
class AISignal:
    """Signal derived from DecisionContract for NautilusTrader strategy."""

    action: str  # "no_trade" | "watch_only" | "wait" | "paper_buy"
    allowed_position_size: float  # 0.0 to 1.0
    rationale: str


class ContractTranslator:
    """Maps DecisionContract to AISignal (same logic as RuleEngine)."""

    def translate(self, contract: DecisionContract) -> AISignal:
        if contract.suggested_action == "forbid_trade":
            return AISignal("no_trade", 0.0, "Contract forbids trade.")
        if contract.confidence == "low":
            return AISignal("watch_only", 0.0, "Confidence too low.")
        if "liquidity_risk" in contract.risk_flags:
            return AISignal("watch_only", 0.0, "Liquidity risk present.")
        if contract.suggested_action == "probe_small":
            return AISignal("paper_buy", 0.25, "Small probe allowed.")
        if contract.suggested_action == "allow_entry" and contract.confidence == "high":
            return AISignal("paper_buy", 1.0, "Full entry allowed.")
        return AISignal("wait", 0.0, "Need further confirmation.")
