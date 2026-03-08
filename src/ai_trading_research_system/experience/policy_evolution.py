"""
Policy Evolution Hooks: 根据 ExperienceInsights 对 PortfolioDecisionPolicy 做微调。
保持 policy 结构不变，仅允许调整 minimum_score_gap、max_replacements、turnover_budget。
"""
from __future__ import annotations

from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy
from ai_trading_research_system.experience.analyzer import ExperienceInsights


def adjust_policy_from_insights(
    policy: PortfolioDecisionPolicy,
    insights: ExperienceInsights,
    *,
    max_delta_min_gap: float = 0.15,
    max_delta_turnover: float = 0.1,
    min_max_replacements: int = 0,
    max_max_replacements: int = 5,
) -> PortfolioDecisionPolicy:
    """
    根据 ExperienceInsights 微调 policy 的 min_gap、max_replacements、turnover_budget。
    结构不变，仅数值在合理范围内小幅调整。
    """
    if not insights.strategy_adjustment_suggested:
        return policy

    min_gap = policy.minimum_score_gap_for_replacement
    max_rep = policy.max_replacements_per_rebalance
    turnover = policy.turnover_budget

    # 频繁因 score_gap 被拒 → 略降 min_gap（更容易替换）
    for f in insights.frequent_replacement_failures or []:
        if "score_gap" in str(f.get("reason", "")).lower() and (f.get("count") or 0) >= 2:
            min_gap = max(0.1, min_gap - 0.05)
            break

    # 风险事件与负超额相关 → 略提高 min_gap（更保守）
    for r in insights.risk_events_correlation or []:
        if (r.get("avg_excess_return") or 0) < -0.02:
            min_gap = min(0.6, min_gap + 0.05)
            break

    # 高 turnover 触发多 → 略降 max_replacements
    for t in insights.triggers_excessive_turnover or []:
        if (t.get("high_turnover_weeks") or 0) >= 2:
            max_rep = max(min_max_replacements, (max_rep - 1))
            break

    # 政策与高超额关联 → 若当前 policy 不在最优 band，可微调 turnover（这里仅做小幅收紧/放宽）
    if insights.policies_associated_higher_excess_return:
        best = insights.policies_associated_higher_excess_return[0]
        if (best.get("avg_excess_return") or 0) > 0.02:
            pass  # 可选：向该 band 靠拢，此处不强制改 turnover

    # 限制在合理范围
    min_gap = max(0.1, min(0.6, min_gap))
    max_rep = max(min_max_replacements, min(max_max_replacements, max_rep))
    turnover = max(0.2, min(0.7, turnover))

    return PortfolioDecisionPolicy(
        minimum_score_gap_for_replacement=min_gap,
        max_replacements_per_rebalance=max_rep,
        turnover_budget=turnover,
        retain_threshold=policy.retain_threshold,
        no_trade_if_improvement_small=policy.no_trade_if_improvement_small,
    )
