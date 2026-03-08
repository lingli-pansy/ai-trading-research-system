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
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
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
