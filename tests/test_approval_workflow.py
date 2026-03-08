"""Approval workflow: Proposal, ApprovalDecision, RunStore, execute_if_approved。"""
from __future__ import annotations

from pathlib import Path

import pytest

from ai_trading_research_system.runtime.proposal import Proposal, ApprovalDecision
from ai_trading_research_system.state.run_store import RunStore


def test_proposal_to_dict_and_from_dict() -> None:
    p = Proposal(
        run_id="run_1",
        timestamp="2026-01-01T12:00:00Z",
        proposal_summary=["SPY ADD 0.05", "NVDA TRIM 0.02"],
        rebalance_plan={"items": [], "no_trade_reason": ""},
        risk_flags=[],
        portfolio_before_summary={"value": 100_000},
        portfolio_exposure={"SPY": 0.5, "NVDA": 0.2},
        recent_experience_summary=[],
        suggested_action="SPY ADD 0.05 | NVDA TRIM 0.02",
    )
    d = p.to_dict()
    assert d["run_id"] == "run_1"
    assert d["proposal_summary"] == ["SPY ADD 0.05", "NVDA TRIM 0.02"]
    p2 = Proposal.from_dict(d)
    assert p2 is not None and p2.run_id == p.run_id and p2.proposal_summary == p.proposal_summary


def test_approval_decision_strict() -> None:
    d = ApprovalDecision(
        run_id="run_1",
        decision="approve",
        reviewer="openclaw",
        reason="ok",
        timestamp="2026-01-01T12:00:00Z",
    )
    assert d.decision == "approve"
    out = d.to_dict()
    assert out["decision"] == "approve"
    d2 = ApprovalDecision.from_dict(out)
    assert d2 is not None and d2.decision == "approve"
    # invalid decision normalizes to defer
    d3 = ApprovalDecision.from_dict({"run_id": "r", "decision": "invalid", "reviewer": "x", "reason": "", "timestamp": ""})
    assert d3 is not None and d3.decision == "defer"


def test_run_store_write_and_read_proposal_and_decision(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    run_id = "approval_run_1"
    store.create_run(run_id, symbols=["NVDA"])
    proposal_data = {
        "run_id": run_id,
        "timestamp": "2026-01-01T12:00:00Z",
        "proposal_summary": ["NVDA OPEN 0.10"],
        "rebalance_plan": {"items": [{"symbol": "NVDA", "target_position": 0.1}], "no_trade_reason": ""},
        "risk_flags": [],
        "portfolio_before_summary": {"value": 10000},
        "portfolio_exposure": {},
        "recent_experience_summary": [],
        "suggested_action": "NVDA OPEN 0.10",
    }
    store.write_proposal(run_id, proposal_data)
    assert (tmp_path / run_id / "artifacts" / "approval_request.json").exists()
    read = store.read_proposal(run_id)
    assert read is not None and read.get("run_id") == run_id and read.get("proposal_summary") == ["NVDA OPEN 0.10"]

    decision_data = {"run_id": run_id, "decision": "approve", "reviewer": "test", "reason": "", "timestamp": "2026-01-01T12:01:00Z"}
    store.write_approval_decision(run_id, decision_data)
    assert (tmp_path / run_id / "artifacts" / "approval_decision.json").exists()
    dec = store.read_approval_decision(run_id)
    assert dec is not None and dec.get("decision") == "approve"


def test_replay_run_includes_proposal_and_approval_decision(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    run_id = "replay_approval_1"
    store.create_run(run_id, symbols=["SPY"])
    store.write_snapshot(run_id, "portfolio_before", {"equity": 10000})
    store.write_proposal(run_id, {"run_id": run_id, "proposal_summary": ["SPY ADD 0.05"], "rebalance_plan": {}, "risk_flags": [], "portfolio_before_summary": {}, "portfolio_exposure": {}, "recent_experience_summary": [], "suggested_action": "", "timestamp": ""})
    store.write_approval_decision(run_id, {"run_id": run_id, "decision": "reject", "reviewer": "u", "reason": "test", "timestamp": ""})
    replay = store.replay_run(run_id)
    assert replay is not None
    assert "proposal" in replay and replay["proposal"] is not None
    assert "approval_decision" in replay and replay["approval_decision"].get("decision") == "reject"
