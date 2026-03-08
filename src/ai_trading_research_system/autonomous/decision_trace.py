"""
Decision Traceability: DecisionTrace、TriggerTrace，用于调仓与触发的可追溯记录。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DecisionTrace:
    """单次分配决策的可追溯记录；含 LLM research reasoning（thesis / key_drivers / risk_factors）。"""
    timestamp: str
    symbol: str
    opportunity_score: float
    health_context: dict[str, Any]
    policy_constraints: dict[str, Any]
    trigger_context: dict[str, Any]
    allocator_reason: str
    final_action: str  # replace | retain | rejected | rebalance | no_trade
    research_thesis: str = ""
    """DecisionContract 中的 thesis（研究结论）。"""
    research_key_drivers: list[str] = field(default_factory=list)
    """DecisionContract 中的 key_drivers。"""
    research_risk_factors: list[str] = field(default_factory=list)
    """DecisionContract 中的 risk_flags，作为 research risk factors。"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "opportunity_score": self.opportunity_score,
            "health_context": self.health_context,
            "policy_constraints": self.policy_constraints,
            "trigger_context": self.trigger_context,
            "allocator_reason": self.allocator_reason,
            "final_action": self.final_action,
            "research_thesis": self.research_thesis,
            "research_key_drivers": self.research_key_drivers,
            "research_risk_factors": self.research_risk_factors,
        }


@dataclass
class TriggerTrace:
    """单次 trigger 评估记录（无论是否触发）。"""
    timestamp: str
    trigger_fired: bool
    trigger_type: str = ""
    trigger_reason: str = ""
    health_context: dict[str, Any] = field(default_factory=dict)
    severity: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "trigger_fired": self.trigger_fired,
            "trigger_type": self.trigger_type,
            "trigger_reason": self.trigger_reason,
            "health_context": self.health_context,
            "severity": self.severity,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
