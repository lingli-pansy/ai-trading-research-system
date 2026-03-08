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
