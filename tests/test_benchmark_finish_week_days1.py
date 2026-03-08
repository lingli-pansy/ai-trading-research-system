"""
UC-09: 1-day benchmark return 边界条件。finish_week 使用 lookback_days=max(2, duration_days)，保证至少 2 根 bar 用于收益计算。
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.services.weekly_finish_service import finish_week
from ai_trading_research_system.pipeline.weekly_paper_pipe import run_weekly_autonomous_paper, WeeklyPaperResult


def test_benchmark_return_days_1():
    """finish_week(duration_days=1) 应调用 get_benchmark_return(lookback_days=2)，避免 1 根 bar 无法算收益。"""
    mandate = WeeklyTradingMandate(
        mandate_id="test_mandate_1",
        capital_limit=10_000.0,
        benchmark="SPY",
        duration_trading_days=1,
        watchlist=["SPY"],
    )
    with patch("ai_trading_research_system.services.weekly_finish_service.get_benchmark_return") as m:
        m.return_value = (0.0, "mock")
        result = finish_week(
            mandate=mandate,
            capital=10_000.0,
            benchmark="SPY",
            duration_days=1,
            total_pnl=0.0,
            total_trades=0,
            run_ids=[],
            key_trades=[],
            no_trade_reasons=[],
            daily_research=[],
            snapshot_source="mock",
            use_mock=True,
            state="completed_week",
            report_dir=Path("."),
        )
        m.assert_called_once()
        call_kw = m.call_args[1]
        assert call_kw["lookback_days"] == 2, "duration_days=1 时应使用 lookback_days=2"


def test_finish_week_days_1_generates_report():
    """duration_days=1 时 weekly-paper 应完整跑通并生成周报（use_mock=True）。"""
    result = run_weekly_autonomous_paper(
        capital=10_000.0,
        benchmark="SPY",
        duration_days=1,
        use_mock=True,
        symbols=["SPY"],
    )
    assert isinstance(result, WeeklyPaperResult)
    assert result.ok is True
    assert result.report_path, "应生成 report_path"
    assert isinstance(result.summary, dict)
    assert "snapshot_source" in result.summary
    assert "benchmark_source" in result.summary


def test_real_mode_days_1_no_mock_fallback():
    """duration_days=1 且 use_mock=False 时，finish_week 通过 lookback_days=2 取 benchmark，不因 1 根 bar 抛错。"""
    mandate = WeeklyTradingMandate(
        mandate_id="test_mandate_real_1",
        capital_limit=10_000.0,
        benchmark="SPY",
        duration_trading_days=1,
        watchlist=["SPY"],
    )
    with patch("ai_trading_research_system.services.weekly_finish_service.get_benchmark_return") as m:
        m.return_value = (0.01, "ib")
        result = finish_week(
            mandate=mandate,
            capital=10_000.0,
            benchmark="SPY",
            duration_days=1,
            total_pnl=0.0,
            total_trades=0,
            run_ids=[],
            key_trades=[],
            no_trade_reasons=[],
            daily_research=[],
            snapshot_source="ibkr",
            use_mock=False,
            state="completed_week",
            report_dir=Path("."),
        )
        m.assert_called_once()
        call_kw = m.call_args[1]
        assert call_kw["lookback_days"] == 2
        assert call_kw["reject_mock"] is True
        assert result.summary.get("benchmark_source") == "ib"
