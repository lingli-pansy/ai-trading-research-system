"""ExperienceStore: get_recent_runs, get_symbol_history, get_recent_rebalances。"""
from __future__ import annotations

from pathlib import Path

import pytest

from ai_trading_research_system.state.run_store import RunStore
from ai_trading_research_system.state.experience_store import ExperienceStore, get_experience_store


def test_experience_store_get_recent_runs(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    store.append_experience({"run_id": "r1", "timestamp": "2026-01-01T09:00:00Z", "symbols": ["NVDA"], "rebalance_plan": {}, "decision_summary": "a", "portfolio_before": {}, "portfolio_after": {}})
    store.append_experience({"run_id": "r2", "timestamp": "2026-01-01T10:00:00Z", "symbols": ["SPY"], "rebalance_plan": {}, "decision_summary": "b", "portfolio_before": {}, "portfolio_after": {}})
    exp = ExperienceStore(root=tmp_path)
    recent = exp.get_recent_runs(2)
    assert len(recent) == 2
    assert recent[0]["run_id"] == "r2"
    assert recent[1]["run_id"] == "r1"


def test_experience_store_get_symbol_history(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    store.append_experience({"run_id": "r1", "timestamp": "T1", "symbols": ["NVDA", "SPY"], "rebalance_plan": {}, "decision_summary": "", "portfolio_before": {}, "portfolio_after": {}})
    store.append_experience({"run_id": "r2", "timestamp": "T2", "symbols": ["SPY"], "rebalance_plan": {}, "decision_summary": "", "portfolio_before": {}, "portfolio_after": {}})
    exp = ExperienceStore(root=tmp_path)
    nvda = exp.get_symbol_history("NVDA")
    assert len(nvda) == 1 and nvda[0]["run_id"] == "r1"
    spy = exp.get_symbol_history("SPY")
    assert len(spy) == 2


def test_experience_store_get_recent_rebalances(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    store.append_experience({
        "run_id": "r1", "timestamp": "T1", "symbols": ["NVDA"],
        "rebalance_plan": {"items": [{"symbol": "NVDA", "delta": 0.1}]},
        "decision_summary": "add",
        "portfolio_before": {},
        "portfolio_after": {},
    })
    exp = ExperienceStore(root=tmp_path)
    rebalances = exp.get_recent_rebalances("NVDA", limit=5)
    assert len(rebalances) == 1
    assert rebalances[0]["run_id"] == "r1"
    assert "rebalance_plan" in rebalances[0]
