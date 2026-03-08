"""
Opportunity Ranking: DecisionContracts -> ranked OpportunityScores.
Based on confidence, thesis strength, risk flags, momentum/price summary.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai_trading_research_system.research.schemas import DecisionContract


@dataclass
class OpportunityScore:
    symbol: str
    score: float
    confidence: str
    risk: str  # "low" | "medium" | "high"
    thesis_strength: float = 0.0
    suggested_action: str = ""


def _confidence_numeric(c: str) -> float:
    if c == "high":
        return 3.0
    if c == "medium":
        return 2.0
    return 1.0


def _risk_level(contract: DecisionContract) -> str:
    n = len(contract.risk_flags or []) + len(contract.uncertainties or [])
    if n == 0:
        return "low"
    if n <= 2:
        return "medium"
    return "high"


def _thesis_strength(contract: DecisionContract) -> float:
    t = (contract.thesis or "").strip()
    return min(1.0, len(t) / 200.0)


def _score(contract: DecisionContract) -> float:
    conf = _confidence_numeric(contract.confidence)
    strength = _thesis_strength(contract)
    risk_penalty = 0.0
    if _risk_level(contract) == "medium":
        risk_penalty = 0.3
    elif _risk_level(contract) == "high":
        risk_penalty = 0.6
    return conf + strength - risk_penalty


class OpportunityRanking:
    """Rank opportunities from DecisionContracts by score (confidence + thesis strength - risk)."""

    def rank(
        self,
        contracts: list[tuple[str, DecisionContract]],
        *,
        price_summaries: dict[str, str] | None = None,
    ) -> list[OpportunityScore]:
        """
        contracts: list of (symbol, contract).
        price_summaries: optional symbol -> price_summary for momentum (currently unused, for extension).
        Returns list of OpportunityScore sorted by score descending.
        """
        price_summaries = price_summaries or {}
        scored: list[OpportunityScore] = []
        for symbol, contract in contracts:
            s = _score(contract)
            risk = _risk_level(contract)
            strength = _thesis_strength(contract)
            scored.append(OpportunityScore(
                symbol=symbol,
                score=round(s, 4),
                confidence=contract.confidence,
                risk=risk,
                thesis_strength=round(strength, 4),
                suggested_action=contract.suggested_action,
            ))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored
