"""
Autonomous Trading Agent runtime: run_once + run_loop.
Load portfolio → autonomous_paper_cycle → update run index & experience → return summary.
run_loop 内 try/except 包裹 run_once，单次错误不终止 agent，记录并更新 health 后继续。
"""
from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_trading_research_system.agent.health import (
    get_health,
    update_health_success,
    update_health_error,
    mark_agent_stopped,
    should_stop_loop,
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
        from ai_trading_research_system.application.commands.run_autonomous_paper_cycle import (
            run_autonomous_paper_cycle,
        )

        store = self._store_ref()
        # 真实 paper 时：仅当存在本地 portfolio_after 时用作 override，否则传 None 由 cycle 内用已建 session 拉 snapshot，避免重复连接
        if self.use_mock:
            portfolio_state = store.get_latest_portfolio_state(use_mock=True)
        else:
            rid = store.read_latest_run_id()
            portfolio_state = store.read_snapshot(rid, "portfolio_after") if rid else None
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
        order_intents_count = len(out.order_intents) if out.order_intents else 0
        paper_results = getattr(out, "paper_execution_results", None) or []
        executed_orders_count = sum(1 for r in paper_results if r.get("order_done"))
        trade_count = sum(int(r.get("trade_count", 0)) for r in paper_results)
        execution_status = "executed" if (executed_orders_count > 0 or trade_count > 0) else "no_fills"
        if not paper_results and order_intents_count == 0:
            execution_status = "skipped"
        value_after = _portfolio_value(portfolio_after)
        value_before = _portfolio_value(portfolio_before)
        turnover = sum(abs(x.get("delta", 0) or 0) for x in (rebalance_plan.get("items") or []))
        position_count = len(portfolio_after.get("positions", [])) if portfolio_after else 0
        if position_count == 0 and rebalance_plan:
            position_count = len([x for x in (rebalance_plan.get("items") or []) if (x.get("target_position") or 0) > 0])
        risk_flags = getattr(out, "risk_flags", None) or []
        approval_decision = getattr(out, "approval_decision", "") or ""

        index_entry = RunIndexEntry(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbols=symbols,
            decision_summary=decision_summary,
            portfolio_value=value_after,
            orders=executed_orders_count,
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
            approval_decision=approval_decision,
        )
        store.append_experience(experience.to_dict())

        if out.ok:
            update_health_success(store, run_id)
        return {
            "run_id": run_id,
            "ok": out.ok,
            "rebalance_plan": rebalance_plan,
            "rebalance_summary": _format_plan_summary(rebalance_plan),
            "order_intents_count": order_intents_count,
            "executed_orders_count": executed_orders_count,
            "trade_count": trade_count,
            "execution_status": execution_status,
            "portfolio_before_value": value_before,
            "portfolio_after_value": value_after,
            "portfolio_after_source": (portfolio_after or {}).get("source", ""),
            "decision_summary": decision_summary,
            "turnover": turnover,
            "position_count": position_count,
            "risk_flags": risk_flags,
            "approval_decision": approval_decision,
        }

    def run_loop(
        self,
        interval_seconds: float = 300.0,
        max_consecutive_failures: int = 5,
        on_run_done: Callable[[dict[str, Any] | None, str | None], None] | None = None,
    ) -> None:
        """
        while True: try run_once(); on success update health; on exception record error, update health, continue.
        若连续失败超过 max_consecutive_failures 则停止 loop。
        on_run_done(summary, error): 每轮结束后回调，成功时 error=None，异常时 summary=None。
        """
        store = self._store_ref()
        summary: dict[str, Any] | None = None
        error_message: str | None = None
        while True:
            summary = None
            error_message = None
            try:
                summary = self.run_once()
                if summary.get("ok"):
                    pass  # already updated in run_once
                else:
                    update_health_error(store, summary.get("decision_summary") or "run_not_ok")
            except Exception as e:
                error_message = str(e)
                update_health_error(store, error_message)
            if on_run_done:
                on_run_done(summary, error_message)
            health = get_health(store)
            if should_stop_loop(health, max_consecutive_failures=max_consecutive_failures):
                mark_agent_stopped(store)
                if on_run_done:
                    on_run_done(None, "agent_stopped")
                break
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
    单次 run 的可观测输出：RUN, PROPOSAL, RISK FLAGS, APPROVAL, EXECUTION（区分 intents/executed/trade_count/status）, PORTFOLIO。
    供 CLI 或 OpenClaw 直接打印。
    """
    run_id = summary.get("run_id", "")
    plan_lines = summary.get("rebalance_summary") or []
    order_intents_count = summary.get("order_intents_count", 0)
    executed_orders_count = summary.get("executed_orders_count", 0)
    trade_count = summary.get("trade_count", 0)
    execution_status = summary.get("execution_status", "")
    portfolio_after_source = summary.get("portfolio_after_source", "")
    before = summary.get("portfolio_before_value") or 0
    after = summary.get("portfolio_after_value") or 0
    turnover = summary.get("turnover", 0)
    position_count = summary.get("position_count", 0)
    risk_flags = summary.get("risk_flags") or []
    approval = summary.get("approval_decision", "") or "approve"
    parts = [
        f"RUN {run_id}",
        "PROPOSAL",
        *([str(x) for x in plan_lines] if plan_lines else ["(no plan)"]),
        "RISK FLAGS",
        f"turnover={turnover:.2f} position_count={position_count} flags={risk_flags!r}",
        "APPROVAL",
        approval,
        "EXECUTION",
        f"ORDER_INTENTS {order_intents_count}",
        f"EXECUTED_ORDERS {executed_orders_count}",
        f"TRADE_COUNT {trade_count}",
        f"EXECUTION_STATUS {execution_status or 'unknown'}",
        "PORTFOLIO",
        f"value {before:.0f} → {after:.0f}",
        f"portfolio_after.source {portfolio_after_source}",
    ]
    return "\n".join(parts)
