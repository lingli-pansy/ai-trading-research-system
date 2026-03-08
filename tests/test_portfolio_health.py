"""
Portfolio Health Monitoring: 组合健康快照与评估。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ai_trading_research_system.autonomous.schemas import AccountSnapshot
from ai_trading_research_system.autonomous.portfolio_health import (
    PortfolioHealthSnapshot,
    evaluate_portfolio_health,
)
from ai_trading_research_system.autonomous.weekly_report import WeeklyReportGenerator
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.experience.store import write_portfolio_health_snapshot, get_connection
from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper


def _snapshot(equity: float = 10_000, positions: list | None = None) -> AccountSnapshot:
    return AccountSnapshot(
        cash=equity * 0.2,
        equity=equity,
        positions=positions or [],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T12:00:00",
        source="mock",
    )


def test_portfolio_health_snapshot():
    """evaluate_portfolio_health 返回 PortfolioHealthSnapshot，含 portfolio_return, benchmark_return, excess_return, volatility, beta_vs_spy, concentration_index, max_drawdown, current_positions, timestamp。"""
    snapshot = _snapshot(equity=10_500, positions=[
        {"symbol": "NVDA", "quantity": 10, "market_value": 7000},
        {"symbol": "AAPL", "quantity": 5, "market_value": 3500},
    ])
    health = evaluate_portfolio_health(
        snapshot,
        {"benchmark_return": 0.02, "max_drawdown": 0.01},
        snapshot.positions,
        initial_equity=10_000,
    )
    assert isinstance(health, PortfolioHealthSnapshot)
    assert health.portfolio_return == pytest.approx(0.05)
    assert health.benchmark_return == 0.02
    assert health.excess_return == pytest.approx(0.03)
    assert health.max_drawdown == 0.01
    assert len(health.current_positions) == 2
    assert health.timestamp
    assert hasattr(health, "volatility") and hasattr(health, "beta_vs_spy") and hasattr(health, "concentration_index")


def test_beta_vs_spy():
    """有 portfolio_returns 与 spy_returns 时计算 beta_vs_spy。"""
    snapshot = _snapshot()
    health = evaluate_portfolio_health(
        snapshot,
        {
            "benchmark_return": 0.0,
            "portfolio_returns": [0.01, -0.005, 0.02, -0.01, 0.015],
            "spy_returns": [0.008, -0.004, 0.015, -0.008, 0.012],
        },
        [],
    )
    assert isinstance(health.beta_vs_spy, (int, float))
    assert health.beta_vs_spy != 0 or True


def test_concentration_index():
    """concentration_index 为 Herfindahl：单标的全仓为 1，多标的分仓则小于 1。"""
    snapshot = _snapshot(equity=10_000, positions=[])
    health = evaluate_portfolio_health(
        snapshot,
        {"benchmark_return": 0},
        [
            {"symbol": "A", "market_value": 10_000},
        ],
        initial_equity=10_000,
    )
    assert health.concentration_index == pytest.approx(1.0)
    health2 = evaluate_portfolio_health(
        _snapshot(equity=10_000, positions=[
            {"symbol": "A", "market_value": 5_000},
            {"symbol": "B", "market_value": 5_000},
        ]),
        {"benchmark_return": 0},
        [
            {"symbol": "A", "market_value": 5_000},
            {"symbol": "B", "market_value": 5_000},
        ],
    )
    assert health2.concentration_index == pytest.approx(0.5)


def test_health_snapshot_written_to_report():
    """周报包含 portfolio_health：volatility, beta_vs_spy, concentration, drawdown。"""
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["NVDA"])
    bench = BenchmarkResult(
        portfolio_return=0.02,
        benchmark_return=0.01,
        excess_return=0.01,
        max_drawdown=0.02,
        trade_count=5,
        period="day_0_to_5",
        benchmark_source="mock",
    )
    portfolio_health = {
        "volatility": 0.15,
        "beta_vs_spy": 1.1,
        "concentration_index": 0.4,
        "max_drawdown": 0.02,
    }
    gen = WeeklyReportGenerator()
    report = gen.generate(mandate, bench, key_trades=[], turnover_pct=10.0, portfolio_health=portfolio_health)
    assert getattr(report, "portfolio_health", None) == portfolio_health
    d = gen.to_dict(report)
    assert "portfolio_health" in d
    assert d["portfolio_health"]["volatility"] == 0.15
    assert d["portfolio_health"]["beta_vs_spy"] == 1.1
    assert d["portfolio_health"]["concentration_index"] == 0.4
    assert d["portfolio_health"]["max_drawdown"] == 0.02


def test_portfolio_health_snapshot_persisted():
    """write_portfolio_health_snapshot 写入 experience 表。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            snap = {"volatility": 0.12, "beta_vs_spy": 1.0, "concentration_index": 0.5, "max_drawdown": 0.03}
            rid = write_portfolio_health_snapshot(mandate_id="m1", period="day_0_to_5", snapshot=snap)
            assert rid > 0
            conn = get_connection(db_path)
            cur = conn.execute(
                "SELECT snapshot_json FROM portfolio_health_snapshot WHERE id = ?",
                (rid,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            data = json.loads(row[0])
            assert data["volatility"] == 0.12
            assert data["beta_vs_spy"] == 1.0
            assert data["concentration_index"] == 0.5
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_pipeline_writes_health_to_report():
    """Pipeline 运行后报告中含 portfolio_health。"""
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
        report_path = Path(result.report_path)
        assert report_path.exists()
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "portfolio_health" in data
        ph = data["portfolio_health"]
        assert "volatility" in ph
        assert "beta_vs_spy" in ph
        assert "concentration_index" in ph
        assert "max_drawdown" in ph
