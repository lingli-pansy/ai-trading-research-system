"""
Evolution Approval Boundary: EvolutionProposal → ApprovalBoundary → EvolutionDecision。
Policy 与 strategy 的调整均须经此边界批准后才可应用；不直接修改 StrategySpec。
Evolution Guardrails: PolicyDeltaLimit + validate_policy_adjustment 限制单次调整幅度。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy
from ai_trading_research_system.experience.analyzer import ExperienceInsights
from ai_trading_research_system.experience.policy_evolution import adjust_policy_from_insights
from ai_trading_research_system.experience.refiner import refiner_suggest_from_insights


@dataclass
class PolicyDeltaLimit:
    """Evolution Guardrails：单次 policy 调整允许的最大变化幅度。"""
    max_turnover_budget_change: float = 0.2
    """turnover_budget 允许的最大绝对变化（如 0.5 → 0.7 为 0.2）。"""
    max_replacement_threshold_change: float = 0.15
    """minimum_score_gap_for_replacement / retain_threshold 允许的最大绝对变化。"""
    max_positions_change: int = 1
    """max_replacements_per_rebalance 允许的最大绝对变化。"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_turnover_budget_change": self.max_turnover_budget_change,
            "max_replacement_threshold_change": self.max_replacement_threshold_change,
            "max_positions_change": self.max_positions_change,
        }


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


def validate_policy_adjustment(
    current_policy: PortfolioDecisionPolicy,
    proposed_policy_dict: dict[str, Any],
    limit: PolicyDeltaLimit,
) -> tuple[bool, str]:
    """
    Evolution Guardrails: 检查拟议 policy 相对当前 policy 的变化是否在 limit 内。
    返回 (passed: bool, reason: str)。
    """
    reasons: list[str] = []
    try:
        cur_t = current_policy.turnover_budget
        new_t = float(proposed_policy_dict.get("turnover_budget", cur_t))
        if abs(new_t - cur_t) > limit.max_turnover_budget_change:
            reasons.append(f"turnover_budget 变化 {abs(new_t - cur_t):.2f} 超过上限 {limit.max_turnover_budget_change}")
        cur_gap = current_policy.minimum_score_gap_for_replacement
        new_gap = float(proposed_policy_dict.get("minimum_score_gap_for_replacement", cur_gap))
        if abs(new_gap - cur_gap) > limit.max_replacement_threshold_change:
            reasons.append(f"minimum_score_gap 变化 {abs(new_gap - cur_gap):.2f} 超过上限 {limit.max_replacement_threshold_change}")
        cur_retain = current_policy.retain_threshold
        new_retain = float(proposed_policy_dict.get("retain_threshold", cur_retain))
        if abs(new_retain - cur_retain) > limit.max_replacement_threshold_change:
            reasons.append(f"retain_threshold 变化 {abs(new_retain - cur_retain):.2f} 超过上限 {limit.max_replacement_threshold_change}")
        cur_pos = current_policy.max_replacements_per_rebalance
        new_pos = int(proposed_policy_dict.get("max_replacements_per_rebalance", cur_pos))
        if abs(new_pos - cur_pos) > limit.max_positions_change:
            reasons.append(f"max_replacements_per_rebalance 变化 {abs(new_pos - cur_pos)} 超过上限 {limit.max_positions_change}")
    except (TypeError, ValueError, KeyError) as e:
        return False, f"policy 解析异常: {e}"
    if reasons:
        return False, "; ".join(reasons)
    return True, "guardrail passed"


@dataclass
class EvolutionDecision:
    """审批结果：批准的政策、批准的策略调整、被拒项、原因、是否已自动应用；含 guardrail 结果。"""
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
    guardrail_result: str = "passed"
    """Evolution Guardrails 结果：passed | rejected。"""
    guardrail_reason: str = ""
    """Guardrail 未通过时的原因；通过时可为空或简短说明。"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved_policy": self.approved_policy.to_dict() if self.approved_policy else None,
            "approved_strategy_adjustments": self.approved_strategy_adjustments,
            "rejected_adjustments": self.rejected_adjustments,
            "approval_reason": self.approval_reason,
            "auto_applied": self.auto_applied,
            "guardrail_result": self.guardrail_result,
            "guardrail_reason": self.guardrail_reason,
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
    guardrail_limit: PolicyDeltaLimit | None = None,
) -> EvolutionDecision:
    """
    Approval Boundary: 根据 proposal 与 current_policy 决定批准项与被拒项。
    - Policy: 仅当 proposal.auto_applicable 且 proposal.confidence >= auto_approve_confidence_threshold 时批准为
      由 proposed_policy_adjustments 还原的 Policy，且须通过 validate_policy_adjustment guardrail，否则保持 current_policy。
    - Strategy: 本轮不自动批准策略调整，全部放入 rejected_adjustments。
    """
    rejected: list[dict[str, Any]] = []
    approved_policy: PortfolioDecisionPolicy | None = None
    auto_applied = False
    reason_parts: list[str] = []
    guardrail_result = "passed"
    guardrail_reason = ""
    limit = guardrail_limit or PolicyDeltaLimit()

    # Policy: 仅 auto_applicable 且置信度达标时批准，且通过 guardrail
    if proposal.auto_applicable and proposal.confidence >= auto_approve_confidence_threshold:
        p = proposal.proposed_policy_adjustments
        guardrail_ok, guardrail_reason = validate_policy_adjustment(current_policy, p, limit)
        if not guardrail_ok:
            guardrail_result = "rejected"
            approved_policy = current_policy
            rejected.append({"type": "policy", "reason": f"guardrail: {guardrail_reason}"})
            reason_parts.append(f"policy 因 guardrail 未通过保持当前：{guardrail_reason}")
        else:
            try:
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
                guardrail_result = "rejected"
                guardrail_reason = "解析失败"
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
        guardrail_result=guardrail_result,
        guardrail_reason=guardrail_reason,
    )
