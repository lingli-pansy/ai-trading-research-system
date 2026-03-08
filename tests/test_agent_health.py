"""Agent health: 持久化于 runs/agent_health.json，经 RunStore 读写。"""
from __future__ import annotations

from pathlib import Path

import pytest

from ai_trading_research_system.agent.health import (
    AgentHealthStatus,
    get_health,
    update_health_success,
    update_health_error,
    mark_agent_stopped,
    should_stop_loop,
)
from ai_trading_research_system.state.run_store import RunStore


def test_agent_health_status_from_dict() -> None:
    raw = {
        "last_success_run": "run_001",
        "last_error": "err",
        "consecutive_failures": 2,
        "agent_uptime": "2026-01-01T00:00:00Z",
        "current_state": "running",
    }
    h = AgentHealthStatus.from_dict(raw)
    assert h.last_success_run == "run_001"
    assert h.consecutive_failures == 2
    assert h.current_state == "running"


def test_update_health_success(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    update_health_success(store, "run_20260101_0930")
    assert (tmp_path / "agent_health.json").exists()
    health = get_health(store)
    assert health.last_success_run == "run_20260101_0930"
    assert health.consecutive_failures == 0
    assert health.last_error == ""


def test_update_health_error(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    update_health_error(store, "Connection timeout")
    health = get_health(store)
    assert health.last_error == "Connection timeout"
    assert health.consecutive_failures == 1
    update_health_error(store, "API error")
    health = get_health(store)
    assert health.consecutive_failures == 2


def test_should_stop_loop() -> None:
    assert should_stop_loop(AgentHealthStatus(consecutive_failures=5), max_consecutive_failures=5) is True
    assert should_stop_loop(AgentHealthStatus(consecutive_failures=4), max_consecutive_failures=5) is False
    assert should_stop_loop(AgentHealthStatus(current_state="stopped")) is True
