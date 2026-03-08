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
    """Thesis 长度与内容密度，用于拉开同 confidence/risk 下的分数差。"""
    t = (contract.thesis or "").strip()
    return min(1.0, len(t) / 150.0)  # 稍敏感于长度，便于区分


def _score_raw(contract: DecisionContract) -> float:
    """Raw score (confidence + thesis weight - risk penalty), ~1 to 3."""
    conf = _confidence_numeric(contract.confidence)
    strength = _thesis_strength(contract)
    risk_penalty = 0.0
    if _risk_level(contract) == "medium":
        risk_penalty = 0.3
    elif _risk_level(contract) == "high":
        risk_penalty = 0.6
    return conf + 1.2 * strength - risk_penalty  # thesis 权重略增，提升区分度


def _score(contract: DecisionContract) -> float:
    """Normalized opportunity score in [0.0, 1.0] for trace and probe threshold. 归一化略拉大间距避免多标的同分。"""
    raw = _score_raw(contract)
    return round(max(0.0, min(1.0, (raw - 0.5) / 2.0)), 4)  # 分母 2.0 使典型 raw 1.5–2.5 映射到约 0.5–1.0


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
                score=s,
                confidence=contract.confidence,
                risk=risk,
                thesis_strength=round(strength, 4),
                suggested_action=contract.suggested_action,
            ))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored
