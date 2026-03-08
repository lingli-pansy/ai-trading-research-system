"""
Portfolio Decision Policy: 明确的组合决策策略配置。
用于 Allocator 的 replacement / retain / reject 规则。
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PortfolioDecisionPolicy:
    """
    组合决策策略：控制何时允许替换、最多替换数、 turnover 与保留阈值。
    """
    minimum_score_gap_for_replacement: float = 0.3
    """新机会相对当前最弱持仓的分数差至少达到此值才允许替换。"""
    max_replacements_per_rebalance: int = 2
    """单次 rebalance 最多执行的替换数量。"""
    turnover_budget: float = 0.5
    """单次 rebalance 允许的 turnover 上限（权重变动比例，如 0.5 = 50%）。"""
    retain_threshold: float = 0.0
    """当前持仓分数 >= 此阈值时，视为「可保留」；替换时需满足 min_gap。低于此阈值的持仓更易被替换。"""
    no_trade_if_improvement_small: bool = False
    """若为 True，当潜在改进（分数提升）过小时可不交易（可选，当前仅记录在 rationale）。"""

    def to_dict(self) -> dict:
        return {
            "minimum_score_gap_for_replacement": self.minimum_score_gap_for_replacement,
            "max_replacements_per_rebalance": self.max_replacements_per_rebalance,
            "turnover_budget": self.turnover_budget,
            "retain_threshold": self.retain_threshold,
            "no_trade_if_improvement_small": self.no_trade_if_improvement_small,
        }


def default_policy() -> PortfolioDecisionPolicy:
    """默认策略（保守：要求明显分数差、限制替换数）。"""
    return PortfolioDecisionPolicy(
        minimum_score_gap_for_replacement=0.3,
        max_replacements_per_rebalance=2,
        turnover_budget=0.5,
        retain_threshold=0.0,
        no_trade_if_improvement_small=False,
    )
