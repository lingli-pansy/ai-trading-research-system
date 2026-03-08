"""
Evolution Approval Boundary: EvolutionProposal → ApprovalBoundary → EvolutionDecision。
Policy 与 strategy 的调整均须经此边界批准后才可应用；不直接修改 StrategySpec。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy
from ai_trading_research_system.experience.analyzer import ExperienceInsights
from ai_trading_research_system.experience.policy_evolution import adjust_policy_from_insights
from ai_trading_research_system.experience.refiner import refiner_suggest_from_insights


@dataclass
class EvolutionProposal:
    """进化建议：政策与策略的拟议调整，来源于 ExperienceInsights。"""
    proposed_policy_adjustments: dict[str, Any] = field(default_factory=dict)
    """拟议的 policy 变更（如 to_dict() 或 policy snapshot），不直接改 mandate。"""
    proposed_strategy_adjustments: dict[str, Any] = field(default_factory=dict)
    """拟议的策略层调整（entry_filters / risk_controls / signal_thresholds），不直接改 StrategySpec。"""
    source_insights: dict[str, Any] = field(default_factory=dict)
    """来源 insights 快照（ExperienceInsights.to_dict()）。"""
    confidence: float = 0.0
    """置信度 [0,1]，用于审批边界判断。"""
    rationale: str = ""
    """建议理由。"""
    auto_applicable: bool = False
    """是否允许在满足置信度等条件下自动应用（仅 policy；strategy 不自动应用）。"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposed_policy_adjustments": self.proposed_policy_adjustments,
            "proposed_strategy_adjustments": self.proposed_strategy_adjustments,
            "source_insights": self.source_insights,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "auto_applicable": self.auto_applicable,
        }


@dataclass
class EvolutionDecision:
    """审批结果：批准的政策、批准的策略调整、被拒项、原因、是否已自动应用。"""
    approved_policy: PortfolioDecisionPolicy | None = None
    """批准后的 policy；若未批准则保持调用方当前 policy。"""
    approved_strategy_adjustments: dict[str, Any] = field(default_factory=dict)
    """批准的策略调整（结构化）；默认不自动批准策略变更。"""
    rejected_adjustments: list[dict[str, Any]] = field(default_factory=list)
    """被拒绝的调整项（含类型与原因）。"""
    approval_reason: str = ""
    """审批说明。"""
    auto_applied: bool = False
    """是否在本轮自动应用了 policy 调整。"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved_policy": self.approved_policy.to_dict() if self.approved_policy else None,
            "approved_strategy_adjustments": self.approved_strategy_adjustments,
            "rejected_adjustments": self.rejected_adjustments,
            "approval_reason": self.approval_reason,
            "auto_applied": self.auto_applied,
        }


def build_evolution_proposal_from_insights(
    insights: ExperienceInsights,
    current_policy: PortfolioDecisionPolicy,
    *,
    auto_applicable: bool = False,
    confidence_if_suggested: float = 0.6,
) -> EvolutionProposal:
    """
    从 ExperienceInsights 构建 EvolutionProposal。
    proposed_policy_adjustments = adjust_policy_from_insights 后的 policy.to_dict()；
    proposed_strategy_adjustments = refiner_suggest_from_insights(insights)。
    """
    proposed_policy = adjust_policy_from_insights(current_policy, insights)
    proposed_policy_dict = proposed_policy.to_dict()
    strategy_adj = refiner_suggest_from_insights(insights)
    confidence = confidence_if_suggested if insights.strategy_adjustment_suggested else 0.0
    rationale = "基于历史替换失败、触发换手、政策-超额关联与风险事件相关性生成建议。"
    return EvolutionProposal(
        proposed_policy_adjustments=proposed_policy_dict,
        proposed_strategy_adjustments=strategy_adj,
        source_insights=insights.to_dict(),
        confidence=confidence,
        rationale=rationale,
        auto_applicable=auto_applicable,
    )


def decide_evolution(
    proposal: EvolutionProposal,
    current_policy: PortfolioDecisionPolicy,
    *,
    auto_approve_confidence_threshold: float = 0.6,
) -> EvolutionDecision:
    """
    Approval Boundary: 根据 proposal 与 current_policy 决定批准项与被拒项。
    - Policy: 仅当 proposal.auto_applicable 且 proposal.confidence >= auto_approve_confidence_threshold 时批准为
      由 proposed_policy_adjustments 还原的 Policy，否则保持 current_policy（并将 policy 变更记入 rejected）。
    - Strategy: 本轮不自动批准策略调整，全部放入 rejected_adjustments；approved_strategy_adjustments 为空。
    """
    rejected: list[dict[str, Any]] = []
    approved_policy: PortfolioDecisionPolicy | None = None
    auto_applied = False
    reason_parts: list[str] = []

    # Policy: 仅 auto_applicable 且置信度达标时批准
    if proposal.auto_applicable and proposal.confidence >= auto_approve_confidence_threshold:
        try:
            p = proposal.proposed_policy_adjustments
            approved_policy = PortfolioDecisionPolicy(
                minimum_score_gap_for_replacement=float(p.get("minimum_score_gap_for_replacement", current_policy.minimum_score_gap_for_replacement)),
                max_replacements_per_rebalance=int(p.get("max_replacements_per_rebalance", current_policy.max_replacements_per_rebalance)),
                turnover_budget=float(p.get("turnover_budget", current_policy.turnover_budget)),
                retain_threshold=float(p.get("retain_threshold", current_policy.retain_threshold)),
                no_trade_if_improvement_small=bool(p.get("no_trade_if_improvement_small", current_policy.no_trade_if_improvement_small)),
            )
            auto_applied = True
            reason_parts.append("policy 已按建议自动批准。")
        except (TypeError, ValueError, KeyError):
            rejected.append({"type": "policy", "reason": "proposed_policy_adjustments 解析失败"})
            approved_policy = current_policy
            reason_parts.append("policy 解析失败，保持当前。")
    else:
        approved_policy = current_policy
        if proposal.proposed_policy_adjustments:
            rejected.append({
                "type": "policy",
                "reason": "未启用自动应用或置信度不足" if not proposal.auto_applicable else "置信度低于阈值",
            })
        reason_parts.append("policy 保持当前（未自动批准）。")

    # Strategy: 不自动批准，全部记为 rejected
    if proposal.proposed_strategy_adjustments:
        rejected.append({
            "type": "strategy",
            "reason": "策略调整须经人工审批",
            "adjustments": proposal.proposed_strategy_adjustments,
        })
        reason_parts.append("策略调整待人工审批。")

    return EvolutionDecision(
        approved_policy=approved_policy,
        approved_strategy_adjustments={},
        rejected_adjustments=rejected,
        approval_reason=" ".join(reason_parts),
        auto_applied=auto_applied,
    )
