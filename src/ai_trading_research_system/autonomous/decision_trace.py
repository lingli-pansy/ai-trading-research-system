"""
Decision Traceability: PortfolioDecisionTrace, SymbolDecisionTrace, DecisionTrace, TriggerTrace.
UC-10: 区分 portfolio-level（allocator_reason / trigger / risk）与 symbol-level（symbol / thesis / opportunity_score / key_drivers / risk_factors / final_action）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PortfolioDecisionTrace:
    """组合级决策记录：allocator 原因、触发上下文、风险/健康上下文。"""
    timestamp: str
    allocator_reason: str
    trigger_context: dict[str, Any]
    health_context: dict[str, Any]
    policy_constraints: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_type": "portfolio",
            "timestamp": self.timestamp,
            "allocator_reason": self.allocator_reason,
            "trigger_context": self.trigger_context,
            "health_context": self.health_context,
            "policy_constraints": self.policy_constraints,
        }


@dataclass
class SymbolDecisionTrace:
    """标的级决策记录：symbol、研究结论、opportunity_score、key_drivers、risk_factors、final_action；no_trade 时可选 no_trade_reason。"""
    timestamp: str
    symbol: str
    research_thesis: str
    opportunity_score: float
    key_drivers: list[str]
    risk_factors: list[str]
    final_action: str  # replace | rejected | retain | no_trade | entry
    no_trade_reason: str = ""  # 当 final_action=no_trade 时：wait_confirmation | score_too_low | health_constraint | probe_threshold_not_met | no_valid_signals 等

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "trace_type": "symbol",
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "research_thesis": self.research_thesis,
            "opportunity_score": self.opportunity_score,
            "key_drivers": self.key_drivers,
            "risk_factors": self.risk_factors,
            "final_action": self.final_action,
        }
        if self.no_trade_reason:
            out["no_trade_reason"] = self.no_trade_reason
        return out


@dataclass
class DecisionTrace:
    """单次分配决策的可追溯记录（兼容旧格式）；含 LLM research reasoning。to_dict 带 trace_type 便于报告拆分。"""
    timestamp: str
    symbol: str
    opportunity_score: float
    health_context: dict[str, Any]
    policy_constraints: dict[str, Any]
    trigger_context: dict[str, Any]
    allocator_reason: str
    final_action: str  # replace | retain | rejected | rebalance | no_trade
    research_thesis: str = ""
    research_key_drivers: list[str] = field(default_factory=list)
    research_risk_factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_type": "portfolio" if not self.symbol else "symbol",
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
