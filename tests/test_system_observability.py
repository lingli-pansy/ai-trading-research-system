"""
System Observability: SystemStatusSnapshot、get_system_status、CLI status、report system_snapshot_at_week_end。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ai_trading_research_system.services.status_service import (
    SystemStatusSnapshot,
    get_system_status,
    system_status_skill,
)
from ai_trading_research_system.experience.store import (
    write_experiment_cycle,
    update_experiment_cycle,
    write_portfolio_health_snapshot,
    write_evolution_proposal_snapshot,
    write_intraday_trigger_event,
    get_connection,
)


def test_system_status_snapshot():
    """SystemStatusSnapshot 结构含 experiment_id、cycle_status、last_rebalance_time、last_trigger_event、current_positions、portfolio_health_summary、active_policy、pending_evolution_proposals、last_report_path。"""
    snap = SystemStatusSnapshot(
        experiment_id="exp_01",
        cycle_status="completed",
        last_rebalance_time="2024-01-01T10:00:00",
        last_trigger_event={"trigger_type": "opportunity_spike", "severity": "medium"},
        current_positions=[{"symbol": "NVDA", "market_value": 5000}],
        portfolio_health_summary={"volatility": 0.12, "beta_vs_spy": 1.0},
        active_policy={"minimum_score_gap_for_replacement": 0.3},
        pending_evolution_proposals=[{"confidence": 0.6}],
        last_report_path="/reports/weekly_report_m1.json",
    )
    assert snap.experiment_id == "exp_01"
    assert snap.cycle_status == "completed"
    assert snap.last_report_path == "/reports/weekly_report_m1.json"
    d = snap.to_dict()
    assert "experiment_id" in d
    assert "cycle_status" in d
    assert "last_rebalance_time" in d
    assert "last_trigger_event" in d
    assert "current_positions" in d
    assert "portfolio_health_summary" in d
    assert "active_policy" in d
    assert "pending_evolution_proposals" in d
    assert "last_report_path" in d


def test_status_service_reads_cycle():
    """get_system_status 从 store 读取最新 experiment_cycle，填充 experiment_id、cycle_status、last_rebalance_time 等。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            write_experiment_cycle(
                experiment_id="exp_status_1",
                mandate_id="m1",
                start_time="2024-01-01T00:00:00",
                end_time="2024-01-05T00:00:00",
                status="completed",
                last_rebalance="2024-01-01T09:00:00",
                last_health_check="2024-01-01T09:00:00",
                last_report_generated="2024-01-05T18:00:00",
                cycle_number=1,
                policy_version="v1",
                applied_policies={"minimum_score_gap_for_replacement": 0.35},
                final_performance={"report_path": "/reports/weekly_m1.json"},
                db_path=db_path,
            )
            status = get_system_status(db_path=db_path)
            assert status.experiment_id == "exp_status_1"
            assert status.cycle_status == "completed"
            assert status.last_rebalance_time == "2024-01-01T09:00:00"
            assert status.active_policy.get("minimum_score_gap_for_replacement") == 0.35
            assert status.last_report_path == "/reports/weekly_m1.json"
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_status_includes_policy():
    """get_system_status 包含 active_policy（来自 experiment_cycles.applied_policies）。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            write_experiment_cycle(
                experiment_id="exp_policy",
                mandate_id="m1",
                start_time="2024-01-01T00:00:00",
                status="running",
                applied_policies={
                    "minimum_score_gap_for_replacement": 0.4,
                    "max_replacements_per_rebalance": 1,
                    "turnover_budget": 0.4,
                },
                db_path=db_path,
            )
            status = get_system_status(db_path=db_path)
            assert status.active_policy.get("minimum_score_gap_for_replacement") == 0.4
            assert status.active_policy.get("max_replacements_per_rebalance") == 1
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_status_includes_portfolio_health():
    """get_system_status 包含 portfolio_health_summary、current_positions（来自 portfolio_health_snapshot）。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            write_portfolio_health_snapshot(
                mandate_id="m1",
                period="day_0_to_5",
                snapshot={
                    "volatility": 0.15,
                    "beta_vs_spy": 1.2,
                    "concentration_index": 0.5,
                    "max_drawdown": 0.03,
                    "current_positions": [{"symbol": "AAPL", "market_value": 3000}],
                },
                db_path=db_path,
            )
            status = get_system_status(db_path=db_path)
            assert status.portfolio_health_summary.get("volatility") == 0.15
            assert status.portfolio_health_summary.get("beta_vs_spy") == 1.2
            assert len(status.current_positions) == 1
            assert status.current_positions[0].get("symbol") == "AAPL"
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_weekly_report_includes_system_snapshot_at_week_end():
    """周报含 system_snapshot_at_week_end 字段。"""
    from ai_trading_research_system.autonomous.weekly_report import WeeklyReportGenerator
    from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
    from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["NVDA"])
    bench = BenchmarkResult(
        portfolio_return=0.0,
        benchmark_return=0.0,
        excess_return=0.0,
        max_drawdown=0.0,
        trade_count=0,
        period="day_0_to_5",
        benchmark_source="mock",
    )
    system_snapshot = {
        "experiment_id": "exp_1",
        "cycle_status": "completed",
        "last_report_path": "/reports/weekly_m1.json",
        "active_policy": {"minimum_score_gap_for_replacement": 0.3},
    }
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        bench,
        key_trades=[],
        turnover_pct=0.0,
        system_snapshot_at_week_end=system_snapshot,
    )
    assert getattr(report, "system_snapshot_at_week_end", None) == system_snapshot
    d = gen.to_dict(report)
    assert "system_snapshot_at_week_end" in d
    assert d["system_snapshot_at_week_end"]["experiment_id"] == "exp_1"


def test_system_status_skill_returns_dict():
    """system_status_skill() 返回 SystemStatusSnapshot 的 dict，供 OpenClaw/heartbeat 使用。"""
    out = system_status_skill()
    assert isinstance(out, dict)
    assert "experiment_id" in out
    assert "cycle_status" in out
    assert "active_policy" in out
    assert "portfolio_health_summary" in out


def test_cli_status_command():
    """CLI 支持 status 子命令，输出 system status summary。"""
    import subprocess
    root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        ["uv", "run", "python", "-m", "ai_trading_research_system.presentation.cli", "status"],
        capture_output=True,
        text=True,
        cwd=str(root),
        timeout=15,
    )
    assert result.returncode == 0
    out = result.stdout or result.stderr or ""
    assert "cycle_status" in out or "experiment_id" in out or "no_store" in out or "active_policy" in out
