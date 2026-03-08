"""
Intraday Opportunistic Adjustment Trigger: 仅在有 trigger 时执行 allocator。
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ai_trading_research_system.autonomous.schemas import AccountSnapshot, WeeklyTradingMandate
from ai_trading_research_system.autonomous.portfolio_policy import PortfolioDecisionPolicy
from ai_trading_research_system.autonomous.trigger_evaluator import evaluate_intraday_triggers
from ai_trading_research_system.autonomous.adjustment_trigger import (
    TRIGGER_DRAWDOWN,
    TRIGGER_OPPORTUNITY_SPIKE,
    TRIGGER_RISK_EVENT,
)
from ai_trading_research_system.autonomous.weekly_report import WeeklyReportGenerator
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
from ai_trading_research_system.experience.store import write_intraday_trigger_event, get_connection
from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper


def _snapshot(equity: float = 10_000, positions: list | None = None) -> AccountSnapshot:
    return AccountSnapshot(
        cash=equity * 0.5,
        equity=equity,
        positions=positions or [],
        open_orders=[],
        risk_budget=1000,
        timestamp="2024-01-01T12:00:00",
        source="mock",
    )


def test_drawdown_trigger():
    """drawdown_pct >= threshold 时返回 drawdown_trigger。"""
    snapshot = _snapshot(equity=9_000)
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=0.3, max_replacements_per_rebalance=2, turnover_budget=0.5)
    trigger = evaluate_intraday_triggers(
        snapshot,
        opportunity_ranking=[{"symbol": "A", "score": 1.0, "risk": "low"}],
        current_positions={},
        policy=policy,
        drawdown_pct=6.0,
    )
    assert trigger is not None
    assert trigger.trigger_type == TRIGGER_DRAWDOWN
    assert "drawdown" in trigger.trigger_reason.lower()
    assert trigger.severity in ("medium", "high")


def test_drawdown_trigger_via_initial_equity():
    """通过 initial_equity 计算回撤并触发。"""
    snapshot = _snapshot(equity=9_200)  # 8% down from 10k
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=0.3, max_replacements_per_rebalance=2, turnover_budget=0.5)
    trigger = evaluate_intraday_triggers(
        snapshot,
        opportunity_ranking=[{"symbol": "A", "score": 0.5, "risk": "low"}],
        current_positions={},
        policy=policy,
        initial_equity=10_000,
    )
    assert trigger is not None
    assert trigger.trigger_type == TRIGGER_DRAWDOWN


def test_opportunity_spike_trigger():
    """最优机会分数显著高于当前持仓时返回 opportunity_spike_trigger。"""
    snapshot = _snapshot()
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=0.3, max_replacements_per_rebalance=2, turnover_budget=0.5)
    trigger = evaluate_intraday_triggers(
        snapshot,
        opportunity_ranking=[{"symbol": "NVDA", "score": 2.5, "risk": "low"}],
        current_positions={},
        policy=policy,
    )
    assert trigger is not None
    assert trigger.trigger_type == TRIGGER_OPPORTUNITY_SPIKE
    assert "score" in trigger.trigger_reason or "top" in trigger.trigger_reason.lower()


def test_risk_event_trigger():
    """任一机会 risk=high 时返回 risk_event_trigger。"""
    snapshot = _snapshot()
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=0.3, max_replacements_per_rebalance=2, turnover_budget=0.5)
    trigger = evaluate_intraday_triggers(
        snapshot,
        opportunity_ranking=[
            {"symbol": "A", "score": 1.0, "risk": "low"},
            {"symbol": "B", "score": 2.0, "risk": "high"},
        ],
        current_positions={},
        policy=policy,
    )
    assert trigger is not None
    assert trigger.trigger_type == TRIGGER_RISK_EVENT
    assert trigger.severity == "high"


def test_no_adjustment_without_trigger():
    """无回撤、无风险事件、机会分数不够高时返回 None。"""
    snapshot = _snapshot(equity=10_000)
    policy = PortfolioDecisionPolicy(minimum_score_gap_for_replacement=1.0, max_replacements_per_rebalance=2, turnover_budget=0.5)
    trigger = evaluate_intraday_triggers(
        snapshot,
        opportunity_ranking=[{"symbol": "A", "score": 0.2, "risk": "low"}],
        current_positions={},
        policy=policy,
        drawdown_pct=2.0,
    )
    assert trigger is None


def test_trigger_records_in_report():
    """周报包含 intraday_adjustments：trigger_type, positions_changed, rationale。"""
    mandate = WeeklyTradingMandate(mandate_id="m1", watchlist=["NVDA"])
    bench = BenchmarkResult(
        portfolio_return=0.0,
        benchmark_return=0.0,
        excess_return=0.0,
        max_drawdown=0.0,
        trade_count=0,
        period="day_0_to_1",
        benchmark_source="mock",
    )
    intraday = [
        {"trigger_type": TRIGGER_OPPORTUNITY_SPIKE, "positions_changed": ["NVDA", "AAPL"], "rationale": "top_score_2.5_minus_best_0"},
    ]
    gen = WeeklyReportGenerator()
    report = gen.generate(mandate, bench, key_trades=[], turnover_pct=0.0, intraday_adjustments=intraday)
    assert getattr(report, "intraday_adjustments", None) == intraday
    d = gen.to_dict(report)
    assert "intraday_adjustments" in d
    assert d["intraday_adjustments"][0]["trigger_type"] == TRIGGER_OPPORTUNITY_SPIKE
    assert d["intraday_adjustments"][0]["positions_changed"] == ["NVDA", "AAPL"]
    assert "rationale" in d["intraday_adjustments"][0]


def test_intraday_trigger_event_persisted():
    """write_intraday_trigger_event 写入 experience 表。"""
    with tempfile.TemporaryDirectory() as td:
        import os
        db_path = Path(td) / "exp.db"
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            rid = write_intraday_trigger_event(
                mandate_id="m1",
                period="day_0",
                trigger_type=TRIGGER_OPPORTUNITY_SPIKE,
                trigger_reason="top_score_high",
                severity="medium",
                positions_changed=["NVDA"],
            )
            assert rid > 0
            conn = get_connection(db_path)
            cur = conn.execute(
                "SELECT trigger_type, trigger_reason, severity, positions_changed FROM intraday_trigger_events WHERE id = ?",
                (rid,),
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == TRIGGER_OPPORTUNITY_SPIKE
            assert row[1] == "top_score_high"
            assert row[2] == "medium"
            assert json.loads(row[3]) == ["NVDA"]
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_pipeline_records_intraday_adjustments():
    """Pipeline 在有 trigger 时执行 allocator 并将调整记入报告。"""
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
        assert report_path.exists(), f"Report not found: {report_path}"
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "intraday_adjustments" in data
        assert isinstance(data["intraday_adjustments"], list)
