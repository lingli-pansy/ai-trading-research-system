"""
Experiment Replay: ExperimentReplay、run_experiment_replay、compare_experiment_results、replay 不修改原实验。
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from ai_trading_research_system.services.replay_service import (
    ExperimentReplay,
    ResultComparison,
    run_experiment_replay,
    compare_experiment_results,
    compare_decision_traces,
)
from ai_trading_research_system.pipeline.experiment_cycle import run_experiment_cycle
from ai_trading_research_system.experience.store import (
    read_latest_experiment_cycle,
    read_latest_decision_traces_snapshot,
)


def test_experiment_replay_runs():
    """run_experiment_replay 能完成一次重放并返回 ExperimentReplay（含 replay_result）。"""
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "replay.db"
        report_dir = Path(td)
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            replay = run_experiment_replay(
                "source_exp_1",
                duration_days=1,
                capital=10_000,
                use_mock=True,
                report_dir=report_dir,
                symbols=["NVDA"],
                db_path=db_path,
            )
            assert isinstance(replay, ExperimentReplay)
            assert replay.source_experiment_id == "source_exp_1"
            assert replay.policy_version in ("replay", "")
            assert replay.replay_start
            assert replay.replay_end
            assert isinstance(replay.replay_result, dict)
            assert "portfolio_return" in replay.replay_result or "pnl" in replay.replay_result
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_replay_result_comparison():
    """compare_experiment_results 输出 return_delta、drawdown_delta、turnover_delta。"""
    original = {
        "portfolio_return": 0.02,
        "excess_return": 0.01,
        "max_drawdown": 0.05,
        "turnover_pct": 10.0,
    }
    replay = {
        "portfolio_return": 0.03,
        "excess_return": 0.02,
        "max_drawdown": 0.03,
        "turnover_pct": 15.0,
    }
    comp = compare_experiment_results(original, replay)
    assert isinstance(comp, ResultComparison)
    assert comp.return_delta == pytest.approx(0.01)
    assert comp.drawdown_delta == pytest.approx(-0.02)
    assert comp.turnover_delta == pytest.approx(5.0)
    d = comp.to_dict()
    assert "return_delta" in d
    assert "drawdown_delta" in d
    assert "turnover_delta" in d


def test_replay_does_not_modify_original_experiment():
    """重放使用 replay_<source_experiment_id>，不写入/更新源实验的 experiment_cycles。"""
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "replay.db"
        report_dir = Path(td)
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            cycle, _ = run_experiment_cycle(
                "exp_original",
                cycle_number=1,
                capital=10_000,
                duration_days=1,
                use_mock=True,
                report_dir=report_dir,
                symbols=["NVDA"],
            )
            assert cycle.experiment_id == "exp_original"
            orig = read_latest_experiment_cycle(experiment_id="exp_original", db_path=db_path)
            assert orig is not None
            orig_id = orig.get("experiment_id")
            orig_status = orig.get("status")
            orig_end = orig.get("end_time")

            run_experiment_replay(
                "exp_original",
                duration_days=1,
                use_mock=True,
                report_dir=report_dir,
                symbols=["NVDA"],
                db_path=db_path,
            )

            after = read_latest_experiment_cycle(experiment_id="exp_original", db_path=db_path)
            assert after is not None
            assert after.get("experiment_id") == orig_id
            assert after.get("status") == orig_status
            assert after.get("end_time") == orig_end
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)


def test_weekly_report_replay_analysis_field():
    """WeeklyReport 含 replay_analysis 字段并可序列化。"""
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
    replay_analysis = {
        "source_experiment_id": "exp_1",
        "return_delta": 0.01,
        "drawdown_delta": -0.02,
        "turnover_delta": 5.0,
    }
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        bench,
        key_trades=[],
        turnover_pct=0.0,
        replay_analysis=replay_analysis,
    )
    assert getattr(report, "replay_analysis", None) == replay_analysis
    d = gen.to_dict(report)
    assert "replay_analysis" in d
    assert d["replay_analysis"]["source_experiment_id"] == "exp_1"


def test_decision_diff():
    """compare_decision_traces 输出 position_differences、trigger_differences、policy_constraint_differences。"""
    original_traces = [
        {"symbol": "A", "final_action": "replace", "policy_constraints": {"minimum_score_gap_for_replacement": 0.3}},
        {"symbol": "B", "final_action": "rejected", "policy_constraints": {"minimum_score_gap_for_replacement": 0.3}},
    ]
    original_trigger_traces = [
        {"trigger_fired": True, "trigger_type": "opportunity_spike_trigger", "trigger_reason": "gap_met"},
    ]
    replay_traces = [
        {"symbol": "A", "final_action": "replace", "policy_constraints": {"minimum_score_gap_for_replacement": 0.35}},
        {"symbol": "C", "final_action": "replace", "policy_constraints": {"minimum_score_gap_for_replacement": 0.35}},
    ]
    replay_trigger_traces = [
        {"trigger_fired": True, "trigger_type": "opportunity_spike_trigger", "trigger_reason": "gap_met"},
    ]
    diff = compare_decision_traces(
        original_traces, original_trigger_traces, replay_traces, replay_trigger_traces
    )
    assert "position_differences" in diff
    assert "trigger_differences" in diff
    assert "policy_constraint_differences" in diff
    pd = diff["position_differences"]
    assert "only_in_replay_replace" in pd
    assert "C" in pd["only_in_replay_replace"]
    assert "only_in_original_rejected" in pd
    assert "B" in pd["only_in_original_rejected"]
    td = diff["trigger_differences"]
    assert td["original_fired_count"] == 1
    assert td["replay_fired_count"] == 1
    pc = diff["policy_constraint_differences"]
    assert "original" in pc
    assert "replay" in pc
    assert "deltas" in pc
    assert pc["original"].get("minimum_score_gap_for_replacement") == 0.3
    assert pc["replay"].get("minimum_score_gap_for_replacement") == 0.35
    assert "minimum_score_gap_for_replacement" in pc["deltas"]


def test_replay_trace_comparison():
    """Replay 后 replay_result 含 decision_diff_summary；replay comparison 写入 experience store。"""
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "replay.db"
        report_dir = Path(td)
        os.environ["EXPERIENCE_DB_PATH"] = str(db_path)
        try:
            run_experiment_cycle(
                "exp_trace_src",
                cycle_number=1,
                capital=10_000,
                duration_days=1,
                use_mock=True,
                report_dir=report_dir,
                symbols=["NVDA"],
            )
            snap = read_latest_decision_traces_snapshot(experiment_id="exp_trace_src", db_path=db_path)
            assert snap is not None, "finish_week 应写入 decision_traces_snapshot"

            replay = run_experiment_replay(
                "exp_trace_src",
                duration_days=1,
                use_mock=True,
                report_dir=report_dir,
                symbols=["NVDA"],
                db_path=db_path,
            )
            assert "decision_diff_summary" in replay.replay_result
            diff = replay.replay_result["decision_diff_summary"]
            assert "position_differences" in diff or "trigger_differences" in diff or "policy_constraint_differences" in diff

            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.execute(
                "SELECT source_experiment_id, decision_diff_json FROM replay_comparison ORDER BY id DESC LIMIT 1"
            )
            row = cur.fetchone()
            conn.close()
            assert row is not None
            assert row[0] == "exp_trace_src"
            import json
            decision_diff = json.loads(row[1]) if row[1] else {}
            assert "position_differences" in decision_diff or "trigger_differences" in decision_diff
        finally:
            os.environ.pop("EXPERIENCE_DB_PATH", None)
