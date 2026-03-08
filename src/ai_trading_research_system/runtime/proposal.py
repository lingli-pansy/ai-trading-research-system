"""
Proposal 与 ApprovalDecision：approval workflow 数据结构。
Proposal = runtime 提交给 approver 的交易提案；
ApprovalDecision = approver 的结构化决策（approve | reject | defer）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ApprovalDecisionKind = Literal["approve", "reject", "defer"]


@dataclass
class Proposal:
    """Runtime 提交给 approver 的交易提案。"""
    run_id: str
    timestamp: str
    proposal_summary: list[str]  # 可读摘要，如 ["SPY ADD 0.05", "NVDA TRIM 0.02"]
    rebalance_plan: dict[str, Any]
    risk_flags: list[str]
    portfolio_before_summary: dict[str, Any]  # 至少 value / equity
    portfolio_exposure: dict[str, Any]  # 如各标的权重等
    recent_experience_summary: list[dict[str, Any]]  # 最近 N 次 run 摘要
    suggested_action: str  # 简短建议描述

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "proposal_summary": list(self.proposal_summary),
            "rebalance_plan": dict(self.rebalance_plan),
            "risk_flags": list(self.risk_flags),
            "portfolio_before_summary": dict(self.portfolio_before_summary),
            "portfolio_exposure": dict(self.portfolio_exposure),
            "recent_experience_summary": list(self.recent_experience_summary),
            "suggested_action": self.suggested_action,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "Proposal | None":
        if not data:
            return None
        return cls(
            run_id=str(data.get("run_id", "")),
            timestamp=str(data.get("timestamp", "")),
            proposal_summary=list(data.get("proposal_summary") or []),
            rebalance_plan=dict(data.get("rebalance_plan") or {}),
            risk_flags=list(data.get("risk_flags") or []),
            portfolio_before_summary=dict(data.get("portfolio_before_summary") or {}),
            portfolio_exposure=dict(data.get("portfolio_exposure") or {}),
            recent_experience_summary=list(data.get("recent_experience_summary") or []),
            suggested_action=str(data.get("suggested_action", "")),
        )


@dataclass
class ApprovalDecision:
    """Approver 的决策；必须为 approve | reject | defer。"""
    run_id: str
    decision: ApprovalDecisionKind
    reviewer: str
    reason: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "decision": self.decision,
            "reviewer": self.reviewer,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ApprovalDecision | None":
        if not data:
            return None
        d = data.get("decision", "").strip().lower()
        if d not in ("approve", "reject", "defer"):
            d = "defer"
        return cls(
            run_id=str(data.get("run_id", "")),
            decision=d,  # type: ignore[assignment]
            reviewer=str(data.get("reviewer", "")),
            reason=str(data.get("reason", "")),
            timestamp=str(data.get("timestamp", "")),
        )
