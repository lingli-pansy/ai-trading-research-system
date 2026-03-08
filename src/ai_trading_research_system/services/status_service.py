"""
System Observability: SystemStatusSnapshot、get_system_status()。
聚合 experiment cycle、portfolio health、active policy、trigger state，供 heartbeat / operator inspection。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ai_trading_research_system.experience.store import (
    read_latest_experiment_cycle,
    read_latest_portfolio_health_snapshot,
    read_latest_evolution_proposal,
    read_latest_intraday_trigger,
    get_connection,
    _get_db_path,
)


@dataclass
class SystemStatusSnapshot:
    """系统状态快照：实验周期、最近 rebalance/trigger、持仓、健康摘要、当前政策、待审批进化、最近报告路径。"""
    experiment_id: str = ""
    cycle_status: str = ""
    last_rebalance_time: str = ""
    last_trigger_event: dict[str, Any] = field(default_factory=dict)
    current_positions: list[dict[str, Any]] = field(default_factory=list)
    portfolio_health_summary: dict[str, Any] = field(default_factory=dict)
    active_policy: dict[str, Any] = field(default_factory=dict)
    pending_evolution_proposals: list[dict[str, Any]] = field(default_factory=list)
    last_report_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "cycle_status": self.cycle_status,
            "last_rebalance_time": self.last_rebalance_time,
            "last_trigger_event": self.last_trigger_event,
            "current_positions": self.current_positions,
            "portfolio_health_summary": self.portfolio_health_summary,
            "active_policy": self.active_policy,
            "pending_evolution_proposals": self.pending_evolution_proposals,
            "last_report_path": self.last_report_path,
        }


def get_system_status(
    experiment_id: str | None = None,
    mandate_id: str | None = None,
    db_path: Path | None = None,
) -> SystemStatusSnapshot:
    """
    聚合 experiment cycle、portfolio health、active policy、trigger state，返回 SystemStatusSnapshot。
    用于 heartbeat、operator inspection、CLI status。
    """
    db_path = db_path or _get_db_path()
    if not db_path.exists():
        return SystemStatusSnapshot(cycle_status="no_store")

    cycle = read_latest_experiment_cycle(experiment_id=experiment_id, db_path=db_path)
    health_row = read_latest_portfolio_health_snapshot(mandate_id=mandate_id or (cycle.get("mandate_id") if cycle else None), db_path=db_path)
    proposal_row = read_latest_evolution_proposal(mandate_id=mandate_id or (cycle.get("mandate_id") if cycle else None), db_path=db_path)
    trigger_row = read_latest_intraday_trigger(mandate_id=mandate_id or (cycle.get("mandate_id") if cycle else None), db_path=db_path)

    snapshot = SystemStatusSnapshot()
    if cycle:
        snapshot.experiment_id = cycle.get("experiment_id") or ""
        snapshot.cycle_status = cycle.get("status") or ""
        snapshot.last_rebalance_time = cycle.get("last_rebalance") or cycle.get("start_time") or ""
        applied = cycle.get("applied_policies") or {}
        snapshot.active_policy = applied if isinstance(applied, dict) else {}
        perf = cycle.get("final_performance") or {}
        if isinstance(perf, dict):
            snapshot.last_report_path = perf.get("report_path") or ""
    if health_row:
        snap = health_row.get("snapshot") or {}
        snapshot.portfolio_health_summary = {k: v for k, v in snap.items() if k in ("volatility", "beta_vs_spy", "concentration_index", "max_drawdown", "excess_return", "portfolio_return", "benchmark_return")}
        snapshot.current_positions = snap.get("current_positions") or []
    if proposal_row:
        snapshot.pending_evolution_proposals = [proposal_row.get("proposal") or {}]
    if trigger_row:
        snapshot.last_trigger_event = {
            "period": trigger_row.get("period"),
            "trigger_type": trigger_row.get("trigger_type"),
            "trigger_reason": trigger_row.get("trigger_reason"),
            "severity": trigger_row.get("severity"),
            "created_at": trigger_row.get("created_at"),
        }
    return snapshot


def system_status_skill() -> dict[str, Any]:
    """
    OpenClaw / 外部可调用的 skill：返回 SystemStatusSnapshot 的 dict。
    用于 heartbeat、operator inspection；不修改 OpenClaw contract。
    """
    return get_system_status().to_dict()
