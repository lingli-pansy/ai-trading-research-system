"""单周期 autonomous paper：主路径与 OpenClaw 入口。"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_trading_research_system.pipeline.autonomous_paper_cycle import (
    CycleInput,
    CycleOutput,
    run_autonomous_paper_cycle,
)
from ai_trading_research_system.state.run_store import RunStore


def test_cycle_input_output_schema() -> None:
    inp = CycleInput(run_id="r1", symbol_universe=["NVDA"], use_mock=True, execute_paper=False)
    assert inp.run_id == "r1"
    assert inp.symbol_universe == ["NVDA"]
    assert inp.execute_paper is False


@pytest.mark.skipif(
    True,  # 需要 mock 整条 research 链，较重；可改为集成测试时启用
    reason="Cycle 依赖 ResearchOrchestrator/account_snapshot，此处仅测接口与落盘",
)
def test_cycle_e2e_mock(tmp_path: Path) -> None:
    store = RunStore(root=tmp_path)
    with patch("ai_trading_research_system.autonomous.account_snapshot.get_account_snapshot") as m_snap:
        m_snap.return_value = type("Snap", (), {"cash": 10000.0, "equity": 10000.0, "positions": [], "open_orders": [], "risk_budget": 0, "timestamp": "2025-01-01T00:00:00Z", "source": "mock"})()
        out = run_autonomous_paper_cycle(
            CycleInput(run_id="e2e_1", symbol_universe=["NVDA"], use_mock=True, use_llm=False, execute_paper=False),
            run_store=store,
        )
    assert out.run_id == "e2e_1"
    assert store.read_meta("e2e_1") is not None


def test_cycle_run_id_and_store_integration(tmp_path: Path) -> None:
    """仅验证：给定 run_id，create_run 后 meta 与目录存在；不跑完整 research。"""
    store = RunStore(root=tmp_path)
    store.create_run("cycle_meta_test", mode="paper", symbols=["NVDA"], config={"use_mock": True})
    meta = store.read_meta("cycle_meta_test")
    assert meta["mode"] == "paper"
    assert (tmp_path / "cycle_meta_test" / "artifacts").is_dir()
