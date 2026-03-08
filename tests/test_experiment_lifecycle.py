"""
Experiment Lifecycle Automation: ExperimentCycle、run_experiment_cycle、下一周期初始化、persistence、report 字段。
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ai_trading_research_system.pipeline.experiment_cycle import (
    ExperimentCycle,
    run_experiment_cycle,
    build_next_mandate_from_evolution,
)
from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy
from ai_trading_research_system.experience.store import get_connection, write_experiment_cycle, update_experiment_cycle
from ai_trading_research_system.autonomous.weekly_report import WeeklyReportGenerator
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult


def test_experiment_cycle_creation():
    """ExperimentCycle 可创建，含 experiment_id、mandate、start_time、end_time、status、last_rebalance、last_health_check、last_report_generated。"""
    from ai_trading_research_system.autonomous.mandate import mandate_from_cli
    mandate = mandate_from_cli(capital=10_000, benchmark="SPY", duration_days=5)
    cycle = ExperimentCycle(
        experiment_id="exp_001",
        mandate=mandate,
        start_time="2024-01-01T00:00:00",
        end_time="",
        status="running",
        last_rebalance="2024-01-01T10:00:00",
        last_health_check="2024-01-01T10:00:00",
        last_report_generated="",
        cycle_number=1,
        policy_version="v1",
    )
    assert cycle.experiment_id == "exp_001"
    assert cycle.mandate.mandate_id == mandate.mandate_id
    assert cycle.status == "running"
    assert cycle.cycle_number == 1
    assert cycle.policy_version == "v1"
    d = cycle.to_dict()
    assert "experiment_id" in d
    assert "mandate_id" in d
    assert "start_time" in d
    assert "last_rebalance" in d
    assert "last_health_check" in d
    assert "last_report_generated" in d


def test_cycle_runs_weekly_loop():
    """run_experiment_cycle 能启动一周实验并完成 daily rebalance / trigger / report。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        report_dir = Path(td)
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            cycle, result = run_experiment_cycle(
                "exp_loop_1",
                cycle_number=1,
                capital=10_000,
                duration_days=1,
                use_mock=True,
                report_dir=report_dir,
                symbols=["NVDA"],
            )
            assert cycle.experiment_id == "exp_loop_1"
            assert cycle.status in ("completed", "failed")
            assert cycle.end_time
            assert cycle.last_report_generated
            assert result.mandate_id
            assert hasattr(result, "evolution_decision")
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_cycle_generates_report():
    """run_experiment_cycle 结束后报告含 experiment_id、cycle_number、policy_version。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        report_dir = Path(td)
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            _, result = run_experiment_cycle(
                "exp_report_1",
                cycle_number=2,
                policy_version="cycle_2",
                capital=10_000,
                duration_days=1,
                use_mock=True,
                report_dir=report_dir,
                symbols=["NVDA"],
            )
            assert result.report_path
            report_path = Path(result.report_path)
            assert report_path.exists()
            import json
            with open(report_path, encoding="utf-8") as f:
                data = json.load(f)
            assert data.get("experiment_id") == "exp_report_1"
            assert data.get("cycle_number") == 2
            assert data.get("policy_version") == "cycle_2"
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_cycle_applies_approved_evolution():
    """build_next_mandate_from_evolution 根据 evolution_decision 的 approved_policy 生成下一周期 mandate。"""
    from ai_trading_research_system.autonomous.mandate import mandate_from_cli
    prev = mandate_from_cli(capital=10_000, benchmark="SPY", duration_days=5)
    assert prev.policy.minimum_score_gap_for_replacement == 0.3
    evolution_decision = {
        "approved_policy": {
            "minimum_score_gap_for_replacement": 0.4,
            "max_replacements_per_rebalance": 1,
            "turnover_budget": 0.4,
            "retain_threshold": 0.0,
            "no_trade_if_improvement_small": False,
        },
        "auto_applied": False,
    }
    next_mandate = build_next_mandate_from_evolution(prev, evolution_decision)
    assert next_mandate.policy.minimum_score_gap_for_replacement == 0.4
    assert next_mandate.policy.max_replacements_per_rebalance == 1
    assert next_mandate.policy.turnover_budget == 0.4
    assert next_mandate.capital_limit == prev.capital_limit
    assert next_mandate.watchlist == prev.watchlist
    # 无 approved_policy 时保持原 mandate 参数
    next2 = build_next_mandate_from_evolution(prev, {})
    assert next2.policy.minimum_score_gap_for_replacement == prev.policy.minimum_score_gap_for_replacement


def test_experiment_cycles_persisted():
    """write_experiment_cycle 与 update_experiment_cycle 正确写入/更新 experiment_cycles 表。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            rid = write_experiment_cycle(
                experiment_id="exp_persist",
                mandate_id="m1",
                start_time="2024-01-01T00:00:00",
                status="running",
                cycle_number=1,
                policy_version="v1",
                db_path=db_path,
            )
            assert rid > 0
            update_experiment_cycle(
                experiment_id="exp_persist",
                cycle_number=1,
                end_time="2024-01-05T00:00:00",
                status="completed",
                last_report_generated="2024-01-05T00:00:00",
                evolution_decision={"auto_applied": False},
                final_performance={"pnl": 100},
                db_path=db_path,
            )
            conn = get_connection(db_path)
            cur = conn.execute(
                "SELECT experiment_id, status, end_time, final_performance FROM experiment_cycles WHERE experiment_id = ?",
                ("exp_persist",),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[1] == "completed"
            assert row[2] == "2024-01-05T00:00:00"
            import json
            assert json.loads(row[3])["pnl"] == 100
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_weekly_report_has_experiment_fields():
    """周报生成支持 experiment_id、cycle_number、policy_version。"""
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
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        bench,
        key_trades=[],
        turnover_pct=0.0,
        experiment_id="exp_01",
        cycle_number=3,
        policy_version="cycle_3",
    )
    assert report.experiment_id == "exp_01"
    assert report.cycle_number == 3
    assert report.policy_version == "cycle_3"
    d = gen.to_dict(report)
    assert d["experiment_id"] == "exp_01"
    assert d["cycle_number"] == 3
    assert d["policy_version"] == "cycle_3"
