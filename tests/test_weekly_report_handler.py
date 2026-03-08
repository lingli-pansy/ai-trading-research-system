"""
Verify weekly_report command uses run_weekly_report (report-only); no execution.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_trading_research_system.application.command_registry import run
from ai_trading_research_system.application.commands.run_weekly_report import (
    WeeklyReportCommandResult,
    run_weekly_report,
)


def test_weekly_report_returns_weekly_report_command_result(tmp_path: Path) -> None:
    (tmp_path / "weekly_report_m1.json").write_text(
        json.dumps({"mandate_id": "m1", "period": "day_0_to_1", "trade_count": 2}),
        encoding="utf-8",
    )
    result = run("weekly_report", report_dir=tmp_path)
    assert isinstance(result, WeeklyReportCommandResult)
    assert result.ok is True
    assert result.mandate_id == "m1"
    assert "period" in result.summary or "trade_count" in result.summary
    assert "weekly_report" in result.report_path or "m1" in result.report_path


def test_weekly_report_no_file_returns_ok_false(tmp_path: Path) -> None:
    result = run("weekly_report", report_dir=tmp_path)
    assert isinstance(result, WeeklyReportCommandResult)
    assert result.ok is False
    assert result.report_path == ""
    assert result.mandate_id == ""
    assert result.summary == {}


def test_run_weekly_report_direct(tmp_path: Path) -> None:
    (tmp_path / "weekly_report_xyz.json").write_text(
        json.dumps({"mandate_id": "xyz", "next_week_suggestion": "hold"}),
        encoding="utf-8",
    )
    out = run_weekly_report(report_dir=tmp_path)
    assert out.ok is True
    assert out.mandate_id == "xyz"
    assert out.report_path
    assert isinstance(out.summary, dict)
