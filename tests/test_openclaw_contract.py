"""
OpenClaw command contract: verify input/output schemas are stable.
"""
from __future__ import annotations

import json
import pytest

from ai_trading_research_system.openclaw.contract import (
    OPENCLAW_COMMANDS,
    OpenClawErrorOutput,
    OpenClawSuccessBase,
    ResearchSymbolInput,
    ResearchSymbolOutput,
    BacktestSymbolInput,
    BacktestSymbolOutput,
    RunDemoInput,
    RunDemoOutput,
    WeeklyAutonomousPaperInput,
    WeeklyAutonomousPaperOutput,
    WeeklyReportInput,
    WeeklyReportOutput,
    error_to_dict,
    validate_success_output,
    validate_error_output,
)


def test_openclaw_commands_list():
    assert "research_symbol" in OPENCLAW_COMMANDS
    assert "backtest_symbol" in OPENCLAW_COMMANDS
    assert "run_demo" in OPENCLAW_COMMANDS
    assert "weekly_autonomous_paper" in OPENCLAW_COMMANDS
    assert "weekly_report" in OPENCLAW_COMMANDS
    assert len(OPENCLAW_COMMANDS) == 5


def test_research_symbol_input_schema():
    inp = ResearchSymbolInput(symbol="AAPL")
    assert inp.command == "research_symbol"
    assert inp.symbol == "AAPL"
    d = inp.model_dump()
    assert "command" in d and "symbol" in d


def test_backtest_symbol_input_schema():
    inp = BacktestSymbolInput(symbol="NVDA", start_date="2024-01-01", end_date="2024-01-31")
    assert inp.command == "backtest_symbol"
    assert inp.symbol == "NVDA"
    assert inp.start_date == "2024-01-01"
    assert inp.end_date == "2024-01-31"
    d = inp.model_dump()
    assert "command" in d and "symbol" in d


def test_run_demo_input_schema():
    inp = RunDemoInput(symbol="NVDA")
    assert inp.command == "run_demo"
    assert inp.symbol == "NVDA"


def test_weekly_autonomous_paper_input_schema():
    inp = WeeklyAutonomousPaperInput(capital=20000, benchmark="QQQ", duration=5, auto_confirm=True)
    assert inp.command == "weekly_autonomous_paper"
    assert inp.capital == 20000
    assert inp.benchmark == "QQQ"
    assert inp.duration == 5
    assert inp.auto_confirm is True


def test_weekly_report_input_schema():
    inp = WeeklyReportInput(report_dir=None)
    assert inp.command == "weekly_report"
    assert inp.report_dir is None


def test_research_symbol_output_schema():
    out = ResearchSymbolOutput(
        ok=True,
        command="research_symbol",
        status="ok",
        engine_type="nautilus",
        used_nautilus=True,
        symbol="NVDA",
        contract_action="probe_small",
        contract_confidence="medium",
        thesis_snippet="...",
        raw_contract={},
    )
    d = out.model_dump()
    assert d["ok"] is True
    assert d["command"] == "research_symbol"
    assert d["status"] == "ok"
    assert d["engine_type"] == "nautilus"
    assert d["used_nautilus"] is True
    assert "report_path" in d or "symbol" in d


def test_backtest_symbol_output_schema():
    out = BacktestSymbolOutput(
        ok=True,
        command="backtest_symbol",
        status="ok",
        engine_type="nautilus",
        used_nautilus=True,
        symbol="NVDA",
        contract_action="probe_small",
        contract_confidence="medium",
        sharpe=0.5,
        max_drawdown=0.1,
        win_rate=0.6,
        pnl=100.0,
        trade_count=5,
        strategy_run_id=1,
    )
    d = out.model_dump()
    assert d["ok"] is True
    assert d["command"] == "backtest_symbol"
    assert d["report_path"] is None or isinstance(d["report_path"], str)


def test_run_demo_output_schema():
    out = RunDemoOutput(
        ok=True,
        command="run_demo",
        status="ok",
        engine_type="nautilus",
        used_nautilus=True,
        symbol="NVDA",
        research={},
        strategy={},
        backtest={},
        summary={},
    )
    d = out.model_dump()
    assert d["ok"] is True
    assert d["command"] == "run_demo"
    assert "report_path" in d


def test_weekly_autonomous_paper_output_schema():
    out = WeeklyAutonomousPaperOutput(
        ok=True,
        command="weekly_autonomous_paper",
        status="completed",
        engine_type="nautilus",
        used_nautilus=True,
        mandate_id="m1",
        report_path="/reports/weekly_report_m1.json",
        snapshot_source="mock",
        benchmark_source="yfinance",
    )
    d = out.model_dump()
    assert d["ok"] is True
    assert d["command"] == "weekly_autonomous_paper"
    assert d["report_path"] is not None
    assert "mandate_id" in d


def test_weekly_report_output_schema():
    out = WeeklyReportOutput(
        ok=True,
        command="weekly_report",
        status="ok",
        engine_type="nautilus",
        used_nautilus=True,
        mandate_id="m1",
        report_path="/reports/weekly_report_m1.json",
        summary={"period": "day_0_to_1"},
    )
    d = out.model_dump()
    assert d["ok"] is True
    assert d["command"] == "weekly_report"
    assert "summary" in d


def test_error_schema():
    err = OpenClawErrorOutput(ok=False, command="research_symbol", error_code=1, error_message="fail")
    d = err.model_dump()
    assert d["ok"] is False
    assert d["command"] == "research_symbol"
    assert d["error_code"] == 1
    assert d["error_message"] == "fail"


def test_error_to_dict():
    d = error_to_dict("backtest_symbol", 2, "network error")
    assert d["ok"] is False
    assert d["command"] == "backtest_symbol"
    assert d["error_code"] == 2
    assert d["error_message"] == "network error"
    # JSON-serializable
    s = json.dumps(d, ensure_ascii=False)
    back = json.loads(s)
    assert validate_error_output(back)


def test_validate_success_output():
    assert validate_success_output("research_symbol", {
        "ok": True, "command": "research_symbol", "status": "ok",
        "engine_type": "nautilus", "used_nautilus": True,
    }) is True
    assert validate_success_output("research_symbol", {"ok": False}) is False
    assert validate_success_output("research_symbol", {"ok": True, "command": "other"}) is False


def test_validate_error_output():
    assert validate_error_output({
        "ok": False, "command": "x", "error_code": 1, "error_message": "err",
    }) is True
    assert validate_error_output({"ok": True}) is False
