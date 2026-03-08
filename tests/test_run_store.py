"""RunStore: 统一落盘接口，禁止随手写文件。"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ai_trading_research_system.state.run_store import RunStore


def test_run_store_create_and_write(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    run_id = "test_run_001"
    store.create_run(run_id, mode="paper", symbols=["NVDA"], config={"use_mock": True})
    assert (tmp_path / run_id / "meta.json").exists()
    assert (tmp_path / run_id / "snapshots").is_dir()
    assert (tmp_path / run_id / "artifacts").is_dir()
    assert (tmp_path / run_id / "execution").is_dir()

    meta = store.read_meta(run_id)
    assert meta is not None
    assert meta["run_id"] == run_id
    assert meta["mode"] == "paper"
    assert meta["symbols"] == ["NVDA"]


def test_run_store_portfolio_snapshot(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    run_id = "test_run_002"
    store.create_run(run_id, symbols=["NVDA"])
    store.write_portfolio_snapshot(run_id, "before", {"cash": 10000.0, "equity": 10000.0, "positions": [], "source": "mock", "timestamp": "2025-01-01T00:00:00Z", "risk_budget": 0})
    before = store.read_portfolio_snapshot(run_id, "before")
    assert before is not None
    assert before["cash"] == 10000.0
    assert before["_kind"] == "before"


def test_run_store_audit(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    run_id = "test_run_003"
    store.create_run(run_id)
    store.append_audit(run_id, {"message": "step1"})
    store.append_audit(run_id, {"message": "step2"})
    entries = store.read_audit(run_id)
    assert len(entries) == 2
    assert entries[0]["message"] == "step1"
    assert entries[1]["message"] == "step2"


def test_run_store_list_runs(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    store.create_run("r1", symbols=["A"])
    store.create_run("r2", symbols=["B"])
    runs = store.list_runs(limit=10)
    assert len(runs) == 2
    assert set(runs) == {"r1", "r2"}
    latest = store.read_latest_run_id()
    assert latest in ("r1", "r2")


def test_run_store_read_run_summary(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    run_id = "test_summary"
    store.create_run(run_id, symbols=["NVDA"])
    store.write_portfolio_snapshot(run_id, "before", {"equity": 10000, "source": "mock"})
    store.write_final_decision(run_id, {"no_trade_reason": "no_trigger", "order_intents": []})
    summary = store.read_run_summary(run_id)
    assert summary is not None
    assert summary["run_id"] == run_id
    assert summary["final_decision"]["no_trade_reason"] == "no_trigger"
    assert "portfolio_before" in summary


def test_run_store_replay_run(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    run_id = "replay_1"
    store.create_run(run_id, symbols=["NVDA", "AAPL"])
    store.write_snapshot(run_id, "portfolio_before", {"equity": 10000, "positions": []})
    store.write_snapshot(run_id, "research", {"by_symbol": [{"symbol": "NVDA", "confidence": "medium"}]})
    store.write_artifact(run_id, "rebalance_plan", {"items": [{"symbol": "NVDA", "action_type": "OPEN"}], "no_trade_reason": ""})
    replay = store.replay_run(run_id)
    assert replay is not None
    assert replay["run_id"] == run_id
    assert replay["symbols"] == ["NVDA", "AAPL"]
    assert replay["rebalance_plan"] is not None


def test_run_store_get_latest_run_summary(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    store.create_run("r1", symbols=["A"])
    store.write_artifact("r1", "final_decision", {"order_intents": [{"symbol": "A"}]})
    store.write_snapshot("r1", "portfolio_after", {"equity": 10000})
    summary = store.get_latest_run_summary()
    assert summary is not None
    assert summary["run_id"] == "r1"
    assert "final_decision" in summary
    assert "portfolio_after" in summary


def test_run_store_get_latest_portfolio_state(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    store.create_run("p1", symbols=["X"])
    store.write_snapshot("p1", "portfolio_after", {"equity": 5000, "positions": [], "source": "derived"})
    state = store.get_latest_portfolio_state()
    assert state is not None
    assert state.get("equity") == 5000


def test_run_store_get_previous_research_snapshot(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    store.create_run("res1", symbols=["NVDA"])
    store.write_snapshot("res1", "research", {"by_symbol": [{"symbol": "NVDA", "thesis": "test"}]})
    prev = store.get_previous_research_snapshot("NVDA")
    assert prev is not None
    assert prev.get("symbol") == "NVDA"
    assert prev.get("thesis") == "test"
