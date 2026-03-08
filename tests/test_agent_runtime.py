"""Agent runtime: run_loop 错误守卫与 health 联动。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_trading_research_system.agent.health import get_health
from ai_trading_research_system.agent.runtime import AutonomousTradingAgent, format_run_observability
from ai_trading_research_system.state.run_store import RunStore


def test_run_loop_catches_exception_and_updates_health(tmp_path: Path) -> None:
    """run_once 抛异常时 run_loop 捕获、更新 health；连续失败达阈值后停止。"""
    agent = AutonomousTradingAgent(symbols=["NVDA"], capital=10_000, use_mock=True, runs_root=tmp_path)
    call_count = 0

    def failing_run_once():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("mock_api_error")

    with patch.object(agent, "run_once", side_effect=failing_run_once):
        agent.run_loop(interval_seconds=0.0, max_consecutive_failures=2, on_run_done=lambda s, e: None)
    assert call_count == 2
    store = RunStore(root=tmp_path)
    health = get_health(store)
    assert health.consecutive_failures == 2
    assert health.current_state == "stopped"


def test_format_run_observability_includes_turnover_position_count_risk_flags() -> None:
    """Run summary 可观测输出包含 turnover, position_count, risk_flags。"""
    summary = {
        "run_id": "run_20260101_0930",
        "rebalance_summary": ["SPY ADD 0.05", "NVDA TRIM 0.02"],
        "orders_count": 2,
        "portfolio_before_value": 100000,
        "portfolio_after_value": 100540,
        "turnover": 0.18,
        "position_count": 3,
        "risk_flags": [],
    }
    out = format_run_observability(summary)
    assert "RUN run_20260101_0930" in out
    assert "PROPOSAL" in out and "APPROVAL" in out and "approve" in out
    assert "turnover=0.18" in out
    assert "position_count=3" in out
    assert "flags=[]" in out
    assert "100000" in out and "100540" in out
