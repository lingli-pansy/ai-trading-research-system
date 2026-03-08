"""
Command: 单周期 autonomous paper（OpenClaw agent 主入口）。
唯一入口：run_autonomous_paper_cycle；内部调用 pipeline.autonomous_paper_cycle.run_autonomous_paper_cycle。
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ai_trading_research_system.pipeline.autonomous_paper_cycle import (
    run_autonomous_paper_cycle as _run_cycle,
    CycleInput,
    CycleOutput,
)
from ai_trading_research_system.state.run_store import get_run_store


def run_autonomous_paper_cycle(
    run_id: str = "",
    symbol_universe: list[str] | None = None,
    mode: str = "paper",
    use_mock: bool = False,
    use_llm: bool = False,
    time_window: str | None = None,
    portfolio_snapshot_override: dict[str, Any] | None = None,
    risk_budget: float | None = None,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    execute_paper: bool = True,
    runs_root: Path | None = None,
) -> CycleOutput:
    """
    OpenClaw agent 调用此方法即可触发一轮 autonomous paper cycle。
    读组合 → 研究 → 规则/风控 → 最终决策 → 订单意图（可选执行）→ 落盘。
    所有状态与审计写入 state.RunStore（默认 runs/<run_id>/）。
    """
    if not run_id:
        run_id = f"run_{int(time.time())}"
    symbols = symbol_universe if symbol_universe is not None else ["NVDA"]
    store = get_run_store(root=runs_root)
    inp = CycleInput(
        run_id=run_id,
        symbol_universe=symbols,
        mode=mode,
        use_mock=use_mock,
        use_llm=use_llm,
        time_window=time_window,
        portfolio_snapshot_override=portfolio_snapshot_override,
        risk_budget=risk_budget,
        capital=capital,
        benchmark=benchmark,
        execute_paper=execute_paper,
    )
    return _run_cycle(inp, run_store=store)
