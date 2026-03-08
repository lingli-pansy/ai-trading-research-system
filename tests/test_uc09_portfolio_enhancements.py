"""
UC-09 增强验证：多 symbol、allocator replacement、周报组合指标、experience regime。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ai_trading_research_system.autonomous.allocator import PortfolioAllocator, AllocationResult
from ai_trading_research_system.autonomous.schemas import AccountSnapshot, WeeklyTradingMandate
from ai_trading_research_system.autonomous.weekly_report import WeeklyReportGenerator
from ai_trading_research_system.autonomous.portfolio_health import PortfolioHealthSnapshot
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy
from ai_trading_research_system.services.experience_service import write_weekly_run
from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper


def test_uc09_accepts_multiple_symbols():
    """UC-09 可接收多 symbol（watchlist）并用于 mandate。"""
    result = run_weekly_autonomous_paper(
        capital=10000,
        benchmark="SPY",
        duration_days=1,
        use_mock=True,
        symbols=["NVDA", "AAPL"],
    )
    assert result.ok is True
    assert result.mandate_id
    assert "report_path" in result.summary or result.report_path


def test_allocator_respects_health_state():
    """Allocator 接收 portfolio_health 时收紧策略：高 concentration 降低 max_replacements，高 beta 提高 min_gap，高 drawdown 进一步收紧。"""
    snapshot = AccountSnapshot(
        cash=3000,
        equity=10000,
        positions=[
            {"symbol": "A", "quantity": 10, "market_value": 3500},
            {"symbol": "B", "quantity": 10, "market_value": 3500},
        ],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T00:00:00",
        source="mock",
    )
    mandate = WeeklyTradingMandate(
        mandate_id="m1",
        capital_limit=10000,
        max_positions=2,
        watchlist=["NVDA", "AAPL"],
    )
    allocator = PortfolioAllocator(max_position_pct=0.4)
    signals = [
        {"symbol": "A", "size_fraction": 0.4, "rationale": "hold", "score": 0.6},
        {"symbol": "B", "size_fraction": 0.4, "rationale": "hold", "score": 0.5},
        {"symbol": "NVDA", "size_fraction": 0.4, "rationale": "new", "score": 0.95},
    ]
    out_baseline = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False)
    health_high_conc = PortfolioHealthSnapshot(
        portfolio_return=0.0,
        benchmark_return=0.0,
        excess_return=0.0,
        volatility=0.1,
        beta_vs_spy=1.0,
        concentration_index=0.7,
        max_drawdown=0.02,
        current_positions=snapshot.positions or [],
        timestamp="2024-01-01T12:00:00",
    )
    out_health = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False, portfolio_health=health_high_conc)
    assert "effective_max_replacements" in out_health.policy_summary
    assert "effective_min_gap" in out_health.policy_summary
    # 高 concentration 应使 effective_max_replacements <= policy.max_replacements_per_rebalance (2)
    assert out_health.policy_summary["effective_max_replacements"] <= 2
    # 高 drawdown 时 effective_max_replacements 可被压为 0
    health_high_dd = PortfolioHealthSnapshot(
        portfolio_return=-0.05,
        benchmark_return=0.0,
        excess_return=-0.05,
        volatility=0.2,
        beta_vs_spy=1.0,
        concentration_index=0.3,
        max_drawdown=0.08,
        current_positions=snapshot.positions or [],
        timestamp="2024-01-01T12:00:00",
    )
    out_dd = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False, portfolio_health=health_high_dd)
    assert out_dd.policy_summary.get("effective_max_replacements") == 0
    assert out_dd.policy_summary.get("effective_min_gap", 0) >= 0.3


def test_allocator_replacement_decisions():
    """Allocator 在仓位满且新机会更优时可输出 replacement_decisions。"""
    snapshot = AccountSnapshot(
        cash=5000,
        equity=10000,
        positions=[
            {"symbol": "OLD", "quantity": 10, "market_value": 1000},
        ],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T00:00:00",
        source="mock",
    )
    mandate = WeeklyTradingMandate(
        mandate_id="m1",
        capital_limit=10000,
        max_positions=2,
        watchlist=["NVDA", "AAPL", "MSFT"],
    )
    allocator = PortfolioAllocator(max_position_pct=0.3)
    signals = [
        {"symbol": "NVDA", "size_fraction": 0.3, "rationale": "strong"},
        {"symbol": "AAPL", "size_fraction": 0.25, "rationale": "medium"},
        {"symbol": "MSFT", "size_fraction": 0.2, "rationale": "new_opportunity"},
    ]
    out = allocator.allocate(snapshot, mandate, signals, wait_confirmation=False)
    assert isinstance(out, AllocationResult)
    assert hasattr(out, "target_positions")
    assert hasattr(out, "replacement_decisions")
    assert hasattr(out, "allocation_rationale")
    assert isinstance(out.replacement_decisions, list)
    assert len(out.target_positions) >= 2
    if out.replacement_decisions:
        assert any("symbol_out" in d and "symbol_in" in d for d in out.replacement_decisions)


def test_weekly_report_has_portfolio_metrics():
    """周报包含组合层指标：portfolio_return, benchmark_return, excess_return, max_drawdown, turnover, trade_count。"""
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["NVDA"])
    bench = BenchmarkResult(
        portfolio_return=0.02,
        benchmark_return=0.01,
        excess_return=0.01,
        max_drawdown=0.01,
        trade_count=5,
        period="day_0_to_1",
        benchmark_source="mock",
    )
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        bench,
        key_trades=[],
        turnover_pct=15.0,
    )
    assert report.portfolio_return_pct == 2.0
    assert report.benchmark_return_pct == 1.0
    assert report.excess_return_pct == 1.0
    assert report.max_drawdown_pct == 1.0
    assert report.trade_count == 5
    assert getattr(report, "turnover_pct", None) == 15.0
    d = gen.to_dict(report)
    assert "portfolio_return_pct" in d
    assert "benchmark_return_pct" in d
    assert "excess_return_pct" in d
    assert "max_drawdown_pct" in d
    assert "turnover_pct" in d
    assert "trade_count" in d


def test_experience_store_writes_regime_fields():
    """write_weekly_run 写入的 parameters 包含 regime_tag, spy_trend, vix_level。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            run_id = write_weekly_run(
                "NVDA",
                100.0,
                2,
                extra={"day": 0},
                regime_tag="weekly_paper",
                spy_trend="up",
                vix_level="low",
            )
            assert run_id > 0
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cur = conn.execute(
                "SELECT parameters FROM strategy_run WHERE id = ?",
                (run_id,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            params = json.loads(row[0]) if row[0] else {}
            assert params.get("regime_tag") == "weekly_paper"
            assert params.get("spy_trend") == "up"
            assert params.get("vix_level") == "low"
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_health_adjustments_recorded_in_report():
    """周报区分 portfolio_health_snapshot 与 health_based_adjustments，健康触发的调整单独列出。"""
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
    portfolio_health = {"volatility": 0.12, "beta_vs_spy": 1.1, "concentration_index": 0.5, "max_drawdown": 0.02}
    health_based_adjustments = [
        {"trigger_type": "concentration_risk_trigger", "period": "day_1", "trigger_reason": "concentration_index_0.65_gte_0.6", "severity": "medium"},
        {"trigger_type": "beta_spike_trigger", "period": "day_2", "trigger_reason": "beta_vs_spy_1.6_gte_1.5", "severity": "high"},
    ]
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        bench,
        key_trades=[],
        turnover_pct=0.0,
        portfolio_health=portfolio_health,
        health_based_adjustments=health_based_adjustments,
    )
    assert getattr(report, "portfolio_health", None) == portfolio_health
    assert getattr(report, "health_based_adjustments", None) == health_based_adjustments
    d = gen.to_dict(report)
    assert "portfolio_health" in d
    assert "health_based_adjustments" in d
    assert len(d["health_based_adjustments"]) == 2
    assert d["health_based_adjustments"][0]["trigger_type"] == "concentration_risk_trigger"
    assert d["health_based_adjustments"][1]["trigger_type"] == "beta_spike_trigger"


def test_weekly_report_records_policy():
    """周报记录 mandate 使用的 policy_used：minimum_score_gap, max_replacements, turnover_budget。"""
    policy = PortfolioDecisionPolicy(
        minimum_score_gap_for_replacement=0.5,
        max_replacements_per_rebalance=1,
        turnover_budget=0.4,
        retain_threshold=0.1,
    )
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["NVDA"], policy=policy)
    bench = BenchmarkResult(
        portfolio_return=0.0,
        benchmark_return=0.0,
        excess_return=0.0,
        max_drawdown=0.0,
        trade_count=0,
        period="day_0_to_1",
        benchmark_source="mock",
    )
    gen = WeeklyReportGenerator()
    report = gen.generate(mandate, bench, key_trades=[], turnover_pct=0.0)
    assert getattr(report, "policy_used", None) is not None
    pu = report.policy_used
    assert "minimum_score_gap" in pu
    assert "max_replacements" in pu
    assert "turnover_budget" in pu
    assert pu["minimum_score_gap"] == 0.5
    assert pu["max_replacements"] == 1
    assert pu["turnover_budget"] == 0.4


def test_policy_passed_through_pipeline():
    """Pipeline 从 mandate 取 policy；报告与 experience 中能见到 policy。"""
    with tempfile.TemporaryDirectory() as td:
        report_dir = Path(td)
        result = run_weekly_autonomous_paper(
            capital=10000,
            benchmark="SPY",
            duration_days=1,
            use_mock=True,
            symbols=["NVDA"],
            report_dir=report_dir,
        )
        assert result.ok is True
        assert result.report_path
        report_path = Path(result.report_path)
        assert report_path.exists(), f"Report not found: {report_path}"
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "policy_used" in data
        pu = data["policy_used"]
        assert "minimum_score_gap" in pu
        assert "max_replacements" in pu
        assert "turnover_budget" in pu
