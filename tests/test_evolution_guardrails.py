"""
Evolution Guardrails: PolicyDeltaLimit、validate_policy_adjustment、guardrail 拒绝过大调整。
"""
from __future__ import annotations

import pytest

from ai_trading_research_system.experience.evolution_boundary import (
    PolicyDeltaLimit,
    validate_policy_adjustment,
    EvolutionProposal,
    EvolutionDecision,
    decide_evolution,
)
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy


def test_policy_delta_limit():
    """PolicyDeltaLimit 结构含 max_turnover_budget_change、max_replacement_threshold_change、max_positions_change。"""
    limit = PolicyDeltaLimit(
        max_turnover_budget_change=0.2,
        max_replacement_threshold_change=0.15,
        max_positions_change=1,
    )
    assert limit.max_turnover_budget_change == 0.2
    assert limit.max_replacement_threshold_change == 0.15
    assert limit.max_positions_change == 1
    d = limit.to_dict()
    assert d["max_turnover_budget_change"] == 0.2
    assert d["max_replacement_threshold_change"] == 0.15
    assert d["max_positions_change"] == 1

    current = PortfolioDecisionPolicy(
        minimum_score_gap_for_replacement=0.3,
        max_replacements_per_rebalance=2,
        turnover_budget=0.5,
        retain_threshold=0.0,
    )
    proposed_small = {
        "minimum_score_gap_for_replacement": 0.35,
        "max_replacements_per_rebalance": 2,
        "turnover_budget": 0.55,
        "retain_threshold": 0.0,
        "no_trade_if_improvement_small": False,
    }
    passed, reason = validate_policy_adjustment(current, proposed_small, limit)
    assert passed is True
    assert "passed" in reason.lower() or reason == "guardrail passed"


def test_guardrail_rejects_large_change():
    """validate_policy_adjustment 拒绝超过 limit 的 turnover / threshold / positions 变化；decide_evolution 返回 guardrail_result=rejected。"""
    limit = PolicyDeltaLimit(
        max_turnover_budget_change=0.1,
        max_replacement_threshold_change=0.05,
        max_positions_change=0,
    )
    current = PortfolioDecisionPolicy(
        minimum_score_gap_for_replacement=0.3,
        max_replacements_per_rebalance=2,
        turnover_budget=0.5,
        retain_threshold=0.0,
    )
    proposed_large_turnover = {
        "minimum_score_gap_for_replacement": 0.3,
        "max_replacements_per_rebalance": 2,
        "turnover_budget": 0.7,
        "retain_threshold": 0.0,
        "no_trade_if_improvement_small": False,
    }
    passed, reason = validate_policy_adjustment(current, proposed_large_turnover, limit)
    assert passed is False
    assert "turnover" in reason.lower()

    proposal = EvolutionProposal(
        proposed_policy_adjustments=proposed_large_turnover,
        confidence=0.8,
        auto_applicable=True,
    )
    decision = decide_evolution(proposal, current, guardrail_limit=limit)
    assert decision.guardrail_result == "rejected"
    assert decision.guardrail_reason
    assert decision.approved_policy is current
    assert not decision.auto_applied
    d = decision.to_dict()
    assert d["guardrail_result"] == "rejected"
    assert "guardrail_reason" in d
