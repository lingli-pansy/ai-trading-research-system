"""
Decision Traceability: DecisionTrace、allocator 生成 trace、trigger 记录 trace、trace 含 policy/health 上下文。
"""
from __future__ import annotations

from ai_trading_research_system.autonomous.decision_trace import DecisionTrace, TriggerTrace
from ai_trading_research_system.autonomous.allocator import PortfolioAllocator
from ai_trading_research_system.autonomous.schemas import AccountSnapshot, WeeklyTradingMandate
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy, default_policy
from ai_trading_research_system.autonomous.trigger_evaluator import evaluate_intraday_triggers


def test_decision_trace_created():
    """Allocator 在做 allocation 时生成 DecisionTrace（decision_traces 非空）。"""
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=0.3, max_replacements_per_rebalance=2, turnover_budget=0.5)
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["NVDA"], policy=policy)
    snapshot = AccountSnapshot(cash=5_000, equity=10_000, positions=[], open_orders=[], risk_budget=1000, timestamp="2024-01-01T12:00:00", source="mock")
    allocator = PortfolioAllocator(max_position_pct=0.25)
    result = allocator.allocate(
        snapshot,
        mandate,
        signals=[{"symbol": "NVDA", "score": 0.8, "size_fraction": 0.2, "rationale": "signal"}],
        portfolio_health=None,
        trigger_context={"trigger_type": "opportunity_spike_trigger"},
    )
    assert hasattr(result, "decision_traces")
    assert isinstance(result.decision_traces, list)
    assert len(result.decision_traces) >= 1
    t = result.decision_traces[0]
    assert "timestamp" in t
    assert "allocator_reason" in t
    assert "final_action" in t


def test_trace_contains_policy_context():
    """DecisionTrace 含 policy_constraints 上下文。"""
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=0.4, max_replacements_per_rebalance=1, turnover_budget=0.3)
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["A"], policy=policy)
    snapshot = AccountSnapshot(cash=5_000, equity=10_000, positions=[], open_orders=[], risk_budget=1000, timestamp="2024-01-01T12:00:00", source="mock")
    allocator = PortfolioAllocator(max_position_pct=0.25)
    result = allocator.allocate(
        snapshot,
        mandate,
        signals=[{"symbol": "A", "score": 0.7, "size_fraction": 0.2, "rationale": "r"}],
        trigger_context={},
    )
    assert result.decision_traces
    for trace in result.decision_traces:
        assert "policy_constraints" in trace
        pc = trace["policy_constraints"]
        assert "minimum_score_gap_for_replacement" in pc or "max_replacements_per_rebalance" in pc or pc == {}
        if pc:
            assert pc.get("minimum_score_gap_for_replacement") == 0.4
            break


def test_trace_contains_health_context():
    """DecisionTrace 含 health_context；TriggerTrace 含 health_context。"""
    policy = default_policy()
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["NVDA"], policy=policy)
    snapshot = AccountSnapshot(cash=5_000, equity=10_000, positions=[], open_orders=[], risk_budget=1000, timestamp="2024-01-01T12:00:00", source="mock")
    health = {"concentration_index": 0.5, "beta_vs_spy": 1.0, "max_drawdown": 0.02}
    allocator = PortfolioAllocator(max_position_pct=0.25)
    result = allocator.allocate(
        snapshot,
        mandate,
        signals=[{"symbol": "NVDA", "score": 0.6, "size_fraction": 0.2, "rationale": "r"}],
        portfolio_health=health,
        trigger_context={"trigger_type": "opportunity_spike"},
    )
    assert result.decision_traces
    has_health = any(t.get("health_context") for t in result.decision_traces)
    assert has_health, "at least one trace should have health_context"
    one = next(t for t in result.decision_traces if t.get("health_context"))
    assert one["health_context"].get("concentration_index") == 0.5

    trigger, trigger_trace = evaluate_intraday_triggers(
        snapshot,
        [{"symbol": "NVDA", "score": 0.9, "risk": "low"}],
        {},
        policy,
        portfolio_health=health,
    )
    assert hasattr(trigger_trace, "to_dict")
    tt = trigger_trace.to_dict()
    assert "health_context" in tt
    assert tt["health_context"] is not None


def test_decision_trace_contains_research_reasoning():
    """DecisionTrace 含 research_thesis、research_key_drivers、research_risk_factors（来自 DecisionContract reasoning）。"""
    policy = default_policy()
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["OLD", "NVDA"], policy=policy, max_positions=1)
    snapshot = AccountSnapshot(
        cash=5_000,
        equity=10_000,
        positions=[{"symbol": "OLD", "quantity": 10, "market_value": 2_000}],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T12:00:00",
        source="mock",
    )
    allocator = PortfolioAllocator(max_position_pct=0.25)
    signals_with_research = [
        {"symbol": "OLD", "score": 0.3, "size_fraction": 0.2, "rationale": "incumbent"},
        {
            "symbol": "NVDA",
            "score": 0.75,
            "size_fraction": 0.2,
            "rationale": "LLM thesis",
            "research_thesis": "Strong demand and margin resilience support upside.",
            "research_key_drivers": ["revenue growth", "data center"],
            "research_risk_factors": ["valuation_risk"],
        },
    ]
    result = allocator.allocate(
        snapshot,
        mandate,
        signals=signals_with_research,
        portfolio_health=None,
        trigger_context={},
    )
    assert result.decision_traces
    trace_with_research = next(
        (t for t in result.decision_traces if t.get("symbol") == "NVDA" and (t.get("research_thesis") or t.get("research_key_drivers") or t.get("research_risk_factors"))),
        None,
    )
    assert trace_with_research is not None
    assert trace_with_research.get("research_thesis") == "Strong demand and margin resilience support upside."
    assert trace_with_research.get("research_key_drivers") == ["revenue growth", "data center"]
    assert trace_with_research.get("research_risk_factors") == ["valuation_risk"]
