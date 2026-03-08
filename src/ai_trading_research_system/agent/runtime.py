"""
Autonomous Trading Agent runtime: run_once + run_loop.
Load portfolio → autonomous_paper_cycle → update run index & experience → return summary.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_trading_research_system.application.commands.run_autonomous_paper_cycle import (
    run_autonomous_paper_cycle,
)
from ai_trading_research_system.state.run_store import get_run_store, RunStore
from ai_trading_research_system.state.schemas import RunIndexEntry, ExperienceRecord


def _run_id_now() -> str:
    t = datetime.now(timezone.utc)
    return t.strftime("run_%Y%m%d_%H%M")


def _decision_summary(final_decision: dict[str, Any]) -> str:
    if not final_decision:
        return ""
    no_trade = final_decision.get("no_trade_reason")
    if no_trade:
        return no_trade
    intents = final_decision.get("order_intents") or []
    if not intents:
        return "no_orders"
    parts = []
    for o in intents[:5]:
        sym = o.get("symbol", "")
        action = o.get("action", "")
        size = o.get("size_fraction") or o.get("size")
        parts.append(f"{sym} {action} {size}")
    return "; ".join(parts) if parts else "orders"


def _portfolio_value(snapshot: dict[str, Any] | None) -> float:
    if not snapshot:
        return 0.0
    return float(snapshot.get("equity_estimate", snapshot.get("equity", 0)) or 0)


class AutonomousTradingAgent:
    """
    自治交易 Agent 运行循环：单次 run_once 或持续 run_loop。
    所有 runs/ 读写经 RunStore，不直接操作文件。
    """

    def __init__(
        self,
        *,
        symbols: list[str] | None = None,
        capital: float = 10_000.0,
        benchmark: str = "SPY",
        use_mock: bool = True,
        use_llm: bool = False,
        execute_paper: bool = True,
        runs_root: Path | None = None,
    ):
        self.symbols = symbols or ["NVDA"]
        self.capital = capital
        self.benchmark = benchmark
        self.use_mock = use_mock
        self.use_llm = use_llm
        self.execute_paper = execute_paper
        self._runs_root = runs_root
        self._store: RunStore | None = None

    def _store_ref(self) -> RunStore:
        if self._store is None:
            self._store = get_run_store(root=self._runs_root)
        return self._store

    def run_once(self) -> dict[str, Any]:
        """
        1. 加载最新 portfolio state
        2. 调用 autonomous_paper_cycle
        3. 更新 run index 与 experience log
        4. 返回 run summary（含 run_id, rebalance_summary, orders, portfolio_before/after）
        """
        store = self._store_ref()
        portfolio_state = store.get_latest_portfolio_state()
        last_meta = store.get_last_run()
        symbols = self.symbols
        if last_meta and last_meta.get("symbols"):
            symbols = last_meta["symbols"]

        run_id = _run_id_now()
        out = run_autonomous_paper_cycle(
            run_id=run_id,
            symbol_universe=symbols,
            mode="paper",
            use_mock=self.use_mock,
            use_llm=self.use_llm,
            portfolio_snapshot_override=portfolio_state,
            capital=self.capital,
            benchmark=self.benchmark,
            execute_paper=self.execute_paper,
            runs_root=self._runs_root,
        )

        portfolio_before = store.read_snapshot(run_id, "portfolio_before")
        portfolio_after = store.read_snapshot(run_id, "portfolio_after")
        rebalance_plan = store.read_artifact(run_id, "rebalance_plan") or out.rebalance_plan or {}
        decision_summary = _decision_summary(out.final_decision)
        orders_count = len(out.order_intents) if out.order_intents else 0
        value_after = _portfolio_value(portfolio_after)
        value_before = _portfolio_value(portfolio_before)

        index_entry = RunIndexEntry(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbols=symbols,
            decision_summary=decision_summary,
            portfolio_value=value_after,
            orders=orders_count,
        )
        store.append_run_index(index_entry.to_dict())

        experience = ExperienceRecord(
            run_id=run_id,
            timestamp=index_entry.timestamp,
            symbols=symbols,
            rebalance_plan=rebalance_plan,
            decision_summary=decision_summary,
            portfolio_before=portfolio_before or {},
            portfolio_after=portfolio_after or {},
        )
        store.append_experience(experience.to_dict())

        return {
            "run_id": run_id,
            "ok": out.ok,
            "rebalance_plan": rebalance_plan,
            "rebalance_summary": _format_plan_summary(rebalance_plan),
            "orders_count": orders_count,
            "portfolio_before_value": value_before,
            "portfolio_after_value": value_after,
            "decision_summary": decision_summary,
        }

    def run_loop(self, interval_seconds: float = 300.0) -> None:
        """while True: run_once(); sleep(interval_seconds)."""
        while True:
            self.run_once()
            time.sleep(interval_seconds)


def _format_plan_summary(plan: dict[str, Any]) -> list[str]:
    """PLAN 块：每行 SYMBOL ACTION delta（如 SPY ADD 0.05）。"""
    lines = []
    items = plan.get("items") or []
    if plan.get("no_trade_reason"):
        return [plan["no_trade_reason"]]
    for it in items:
        sym = it.get("symbol", "")
        action = (it.get("action_type") or "HOLD").upper()
        delta = it.get("delta", 0)
        lines.append(f"{sym} {action} {delta:.2f}")
    return lines


def format_run_observability(summary: dict[str, Any]) -> str:
    """
    单次 run 的可观测输出：run_id, PLAN, EXECUTION, PORTFOLIO VALUE。
    供 CLI 或 OpenClaw 直接打印。
    """
    run_id = summary.get("run_id", "")
    plan_lines = summary.get("rebalance_summary") or []
    orders = summary.get("orders_count", 0)
    before = summary.get("portfolio_before_value") or 0
    after = summary.get("portfolio_after_value") or 0
    parts = [
        f"RUN {run_id}",
        "PLAN",
        *([str(x) for x in plan_lines] if plan_lines else ["(no plan)"]),
        "EXECUTION",
        f"{orders} orders",
        "PORTFOLIO VALUE",
        f"{before:.0f} → {after:.0f}",
    ]
    return "\n".join(parts)
