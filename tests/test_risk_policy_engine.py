"""RiskPolicyEngine: 执行前风险检查，filtered_rebalance_plan + risk_flags。"""
from __future__ import annotations

import pytest

from ai_trading_research_system.risk.policy_engine import (
    RiskPolicy,
    RiskCheckResult,
    RiskPolicyEngine,
    plan_to_target_positions,
)


def test_risk_policy_engine_pass_through() -> None:
    """无违反时返回原 plan，risk_flags 为空。"""
    engine = RiskPolicyEngine(RiskPolicy(max_position_size=0.5, max_turnover=0.5, max_orders_per_run=10))
    portfolio = {"equity": 100_000, "cash": 50_000}
    plan = {
        "items": [
            {"symbol": "SPY", "current_position": 0.1, "target_position": 0.15, "delta": 0.05, "action_type": "ADD", "reason": "", "confidence": "medium"},
            {"symbol": "NVDA", "current_position": 0.0, "target_position": 0.10, "delta": 0.10, "action_type": "OPEN", "reason": "", "confidence": "medium"},
        ],
        "no_trade_reason": "",
    }
    result = engine.check(portfolio, plan)
    assert isinstance(result, RiskCheckResult)
    assert len(result.risk_flags) == 0
    assert len(result.filtered_rebalance_plan.get("items", [])) == 2


def test_risk_policy_engine_trim_position_size() -> None:
    """单标的超过 max_position_size 时 trim。"""
    engine = RiskPolicyEngine(RiskPolicy(max_position_size=0.20, max_turnover=0.5))
    portfolio = {"equity": 100_000, "cash": 50_000}
    plan = {
        "items": [
            {"symbol": "NVDA", "current_position": 0.0, "target_position": 0.35, "delta": 0.35, "action_type": "OPEN", "reason": "", "confidence": "medium"},
        ],
        "no_trade_reason": "",
    }
    result = engine.check(portfolio, plan)
    assert any("trim_position" in f for f in result.risk_flags)
    items = result.filtered_rebalance_plan.get("items", [])
    assert len(items) == 1
    assert items[0]["target_position"] == 0.20


def test_plan_to_target_positions() -> None:
    """从 plan dict 提取 target_positions 列表。"""
    plan = {
        "items": [
            {"symbol": "SPY", "target_position": 0.2, "reason": "add"},
            {"symbol": "NVDA", "target_position": 0.1, "reason": "open"},
        ],
        "no_trade_reason": "",
    }
    targets = plan_to_target_positions(plan)
    assert len(targets) == 2
    assert targets[0]["symbol"] == "SPY" and targets[0]["weight_pct"] == 0.2
    assert targets[1]["symbol"] == "NVDA" and targets[1]["weight_pct"] == 0.1
