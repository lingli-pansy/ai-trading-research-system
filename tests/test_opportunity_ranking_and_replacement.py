"""
Opportunity Ranking + Position Replacement: ranking step, allocator respects score, replacement only when new > weakest.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from ai_trading_research_system.research.schemas import DecisionContract
from ai_trading_research_system.autonomous.opportunity_ranking import OpportunityRanking, OpportunityScore
from ai_trading_research_system.autonomous.allocator import PortfolioAllocator, AllocationResult
from ai_trading_research_system.autonomous.schemas import AccountSnapshot, WeeklyTradingMandate
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy


def _contract(symbol: str, confidence: str = "medium", thesis: str = "test", risk_flags: list | None = None, uncertainties: list | None = None) -> DecisionContract:
    return DecisionContract(
        symbol=symbol,
        thesis=thesis,
        key_drivers=[],
        confidence=confidence,
        suggested_action="probe_small",
        risk_flags=risk_flags or [],
        uncertainties=uncertainties or [],
        analysis_time=datetime.now(timezone.utc),
    )


def test_opportunity_ranking():
    """OpportunityRanking produces ranked OpportunityScores from DecisionContracts."""
    ranker = OpportunityRanking()
    contracts = [
        ("NVDA", _contract("NVDA", confidence="high", thesis="strong " * 50)),
        ("AAPL", _contract("AAPL", confidence="low", thesis="weak")),
        ("MSFT", _contract("MSFT", confidence="medium", thesis="mid " * 30)),
    ]
    ranked = ranker.rank(contracts)
    assert len(ranked) == 3
    assert all(isinstance(o, OpportunityScore) for o in ranked)
    assert ranked[0].symbol == "NVDA"
    assert ranked[0].confidence == "high"
    assert ranked[0].score >= ranked[1].score >= ranked[2].score
    assert ranked[2].symbol == "AAPL"
    assert ranked[2].risk in ("low", "medium", "high")


def test_position_replacement():
    """Allocator outputs replacement_decisions when new opportunity score > weakest current holding."""
    snapshot = AccountSnapshot(
        cash=3000,
        equity=10000,
        positions=[
            {"symbol": "OLD1", "quantity": 10, "market_value": 2000},
            {"symbol": "OLD2", "quantity": 5, "market_value": 2000},
        ],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T00:00:00",
        source="mock",
    )
    mandate = WeeklyTradingMandate(mandate_id="m1", max_positions=2, watchlist=["NVDA", "AAPL", "MSFT"])
    allocator = PortfolioAllocator(max_position_pct=0.3)
    signals = [
        {"symbol": "NVDA", "size_fraction": 0.3, "rationale": "top", "score": 3.5},
        {"symbol": "AAPL", "size_fraction": 0.25, "rationale": "mid", "score": 2.0},
        {"symbol": "MSFT", "size_fraction": 0.2, "rationale": "new", "score": 2.8},
    ]
    out = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False)
    assert isinstance(out, AllocationResult)
    assert len(out.target_positions) == 2
    assert len(out.replacement_decisions) >= 1
    for d in out.replacement_decisions:
        assert "symbol_out" in d and "symbol_in" in d and "reason" in d


def test_portfolio_allocator_respects_ranking():
    """Allocator sorts by score and replaces only when new opportunity score > weakest in targets."""
    snapshot = AccountSnapshot(
        cash=5000,
        equity=10000,
        positions=[],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T00:00:00",
        source="mock",
    )
    mandate = WeeklyTradingMandate(mandate_id="m1", max_positions=2, watchlist=["A", "B", "C"])
    allocator = PortfolioAllocator(max_position_pct=0.4)
    signals = [
        {"symbol": "A", "size_fraction": 0.4, "rationale": "best", "score": 3.0},
        {"symbol": "B", "size_fraction": 0.3, "rationale": "second", "score": 2.0},
        {"symbol": "C", "size_fraction": 0.3, "rationale": "third", "score": 1.0},
    ]
    out = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False)
    assert len(out.target_positions) == 2
    symbols_in = {t["symbol"] for t in out.target_positions}
    assert "A" in symbols_in
    assert "B" in symbols_in
    assert "C" not in symbols_in
    scores_in = [t.get("score") for t in out.target_positions if t.get("score") is not None]
    assert sorted(scores_in, reverse=True) == scores_in
    signals_weak_first = [
        {"symbol": "C", "size_fraction": 0.3, "rationale": "weak", "score": 0.5},
        {"symbol": "B", "size_fraction": 0.3, "rationale": "mid", "score": 1.5},
        {"symbol": "A", "size_fraction": 0.4, "rationale": "strong", "score": 2.5},
    ]
    out2 = allocator.allocate(snapshot, mandate, signals_weak_first, wait_confirmation=False)
    assert out2.target_positions[0]["symbol"] == "A"
    assert out2.target_positions[1]["symbol"] == "B"


def test_replacement_requires_minimum_score_gap():
    """Replacement is blocked when new opportunity score gap is below policy minimum."""
    snapshot = AccountSnapshot(
        cash=5000,
        equity=10000,
        positions=[
            {"symbol": "OLD", "quantity": 10, "market_value": 5000},
        ],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T00:00:00",
        source="mock",
    )
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=1.0, max_replacements_per_rebalance=2, turnover_budget=1.0)
    mandate = WeeklyTradingMandate(mandate_id="m1", max_positions=1, watchlist=["OLD", "NEW"], policy=policy)
    allocator = PortfolioAllocator(max_position_pct=0.5)
    # OLD has implicit score 0; NEW has 0.5 -> gap 0.5 < 1.0 -> no replacement
    signals = [
        {"symbol": "NEW", "size_fraction": 0.5, "rationale": "new", "score": 0.5},
    ]
    out = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False)
    assert len(out.target_positions) == 1
    assert out.target_positions[0]["symbol"] == "OLD"
    assert len(out.replacement_decisions) == 0
    assert out.policy_summary.get("replacements_skipped_due_to_threshold", 0) >= 1 or len(out.rejected_opportunities) >= 1
    # Gap 1.5 >= 1.0 -> replacement allowed
    signals2 = [{"symbol": "NEW", "size_fraction": 0.5, "rationale": "new", "score": 1.5}]
    out2 = allocator.allocate(snapshot, mandate, signals2, wait_confirmation=False)
    assert len(out2.target_positions) == 1
    assert out2.target_positions[0]["symbol"] == "NEW"
    assert len(out2.replacement_decisions) == 1


def test_max_replacements_per_rebalance():
    """Allocator does not exceed max_replacements_per_rebalance."""
    snapshot = AccountSnapshot(
        cash=0,
        equity=10000,
        positions=[
            {"symbol": "A", "quantity": 1, "market_value": 2500},
            {"symbol": "B", "quantity": 1, "market_value": 2500},
            {"symbol": "C", "quantity": 1, "market_value": 2500},
        ],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T00:00:00",
        source="mock",
    )
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=0.0, max_replacements_per_rebalance=1, turnover_budget=1.0)
    mandate = WeeklyTradingMandate(mandate_id="m1", max_positions=3, watchlist=["A", "B", "C", "X", "Y", "Z"], policy=policy)
    allocator = PortfolioAllocator(max_position_pct=0.25)
    signals = [
        {"symbol": "X", "size_fraction": 0.25, "rationale": "x", "score": 5.0},
        {"symbol": "Y", "size_fraction": 0.25, "rationale": "y", "score": 4.0},
        {"symbol": "Z", "size_fraction": 0.25, "rationale": "z", "score": 3.0},
    ]
    out = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False)
    assert len(out.replacement_decisions) <= 1
    assert out.policy_summary.get("replacements_executed", 0) <= 1
    assert out.policy_summary.get("replacements_skipped_due_to_budget", 0) >= 1 or len(out.rejected_opportunities) >= 1


def test_rejected_opportunities_recorded():
    """Rejected opportunities appear in rejected_opportunities with reason."""
    snapshot = AccountSnapshot(
        cash=5000,
        equity=10000,
        positions=[{"symbol": "OLD", "quantity": 10, "market_value": 5000}],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T00:00:00",
        source="mock",
    )
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=2.0, max_replacements_per_rebalance=1, turnover_budget=1.0)
    mandate = WeeklyTradingMandate(mandate_id="m1", max_positions=1, watchlist=["OLD", "NEW"], policy=policy)
    allocator = PortfolioAllocator(max_position_pct=0.5)
    signals = [{"symbol": "NEW", "size_fraction": 0.5, "rationale": "new", "score": 0.5}]
    out = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False)
    assert len(out.rejected_opportunities) >= 1
    r = out.rejected_opportunities[0]
    assert "symbol" in r and "reason" in r
    assert r["symbol"] == "NEW"
    assert "below_required" in r["reason"] or "score_gap" in r["reason"]


def test_allocator_policy_respects_current_holdings():
    """Retained positions are current holdings that remain in target; policy affects only replacement."""
    snapshot = AccountSnapshot(
        cash=3000,
        equity=10000,
        positions=[
            {"symbol": "KEEP", "quantity": 5, "market_value": 3500},
            {"symbol": "OUT", "quantity": 5, "market_value": 3500},
        ],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T00:00:00",
        source="mock",
    )
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=0.2, max_replacements_per_rebalance=2, turnover_budget=1.0)
    mandate = WeeklyTradingMandate(mandate_id="m1", max_positions=2, watchlist=["KEEP", "OUT", "IN"], policy=policy)
    allocator = PortfolioAllocator(max_position_pct=0.35)
    # KEEP 2.5, IN 2.8, OUT 0 (implicit). Top two by score: KEEP 2.5, IN 2.8. OUT dropped for IN (gap 2.8 > 0.2).
    signals = [
        {"symbol": "KEEP", "size_fraction": 0.35, "rationale": "keep", "score": 2.5},
        {"symbol": "IN", "size_fraction": 0.35, "rationale": "in", "score": 2.8},
        {"symbol": "OUT", "size_fraction": 0.3, "rationale": "out", "score": 0.0},
    ]
    out = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False)
    assert len(out.target_positions) == 2
    symbols = {t["symbol"] for t in out.target_positions}
    assert "KEEP" in symbols
    assert "IN" in symbols
    assert "OUT" not in symbols
    retained_symbols = {p["symbol"] for p in out.retained_positions}
    assert "KEEP" in retained_symbols
    assert len(out.replacement_decisions) >= 1
    for d in out.replacement_decisions:
        assert d["symbol_out"] == "OUT" and d["symbol_in"] == "IN"


def test_allocator_respects_mandate_policy():
    """Allocator uses mandate.policy only; no separate policy argument."""
    snapshot = AccountSnapshot(
        cash=5000,
        equity=10000,
        positions=[{"symbol": "OLD", "quantity": 10, "market_value": 5000}],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T00:00:00",
        source="mock",
    )
    signals = [{"symbol": "NEW", "size_fraction": 0.5, "rationale": "new", "score": 0.5}]
    allocator = PortfolioAllocator(max_position_pct=0.5)
    # Mandate with strict policy: gap 0.5 < 1.0 -> no replacement
    strict = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=1.0, max_replacements_per_rebalance=2, turnover_budget=1.0)
    mandate_strict = WeeklyTradingMandate(mandate_id="m1", max_positions=1, watchlist=["OLD", "NEW"], policy=strict)
    out_strict = allocator.allocate(snapshot, mandate_strict, signals, wait_confirmation=False)
    assert out_strict.target_positions[0]["symbol"] == "OLD"
    assert len(out_strict.replacement_decisions) == 0
    # Mandate with loose policy: gap 0.5 >= 0.3 -> replacement allowed
    loose = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=0.3, max_replacements_per_rebalance=2, turnover_budget=1.0)
    mandate_loose = WeeklyTradingMandate(mandate_id="m2", max_positions=1, watchlist=["OLD", "NEW"], policy=loose)
    out_loose = allocator.allocate(snapshot, mandate_loose, signals, wait_confirmation=False)
    assert out_loose.target_positions[0]["symbol"] == "NEW"
    assert len(out_loose.replacement_decisions) == 1
