"""
Verify weekly_paper_pipe returns only orchestration result (WeeklyPaperResult), no ad-hoc display objects.
"""
from __future__ import annotations

import pytest

from ai_trading_research_system.pipeline.weekly_paper_pipe import (
    run_weekly_autonomous_paper,
    WeeklyPaperResult,
)


def test_pipe_returns_weekly_paper_result_type():
    """run_weekly_autonomous_paper returns WeeklyPaperResult only."""
    result = run_weekly_autonomous_paper(
        capital=10000,
        benchmark="SPY",
        duration_days=1,
        use_mock=True,
    )
    assert isinstance(result, WeeklyPaperResult)


def test_weekly_paper_result_has_contract_fields():
    """WeeklyPaperResult has ok, command-like, status, report_path, summary."""
    result = run_weekly_autonomous_paper(
        capital=10000,
        benchmark="SPY",
        duration_days=1,
        use_mock=True,
    )
    assert hasattr(result, "ok")
    assert hasattr(result, "mandate_id")
    assert hasattr(result, "status")
    assert hasattr(result, "engine_type")
    assert hasattr(result, "used_nautilus")
    assert hasattr(result, "report_path")
    assert hasattr(result, "summary")
    assert isinstance(result.summary, dict)


def test_result_is_not_raw_dict():
    """Result must be a dataclass/object, not a plain dict (so CLI/adapter can rely on schema)."""
    result = run_weekly_autonomous_paper(
        capital=10000,
        benchmark="SPY",
        duration_days=1,
        use_mock=True,
    )
    assert not isinstance(result, dict)
    assert hasattr(result, "report_path")
    assert isinstance(result.report_path, str) or result.report_path is None
