"""
Report service: generate weekly report and write to JSON file.
Used by UC-09 weekly controller and by application.commands.generate_weekly_report.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
from ai_trading_research_system.autonomous.weekly_report import WeeklyReportGenerator


def generate_and_write(
    mandate: WeeklyTradingMandate,
    benchmark_result: BenchmarkResult,
    *,
    key_trades: list[str] | None = None,
    risk_events: list[str] | None = None,
    no_trade_days: int = 0,
    no_trade_reasons: list[str] | None = None,
    daily_research: list[dict[str, Any]] | None = None,
    report_dir: Path | None = None,
) -> str:
    """Generate weekly report and write to report_dir/weekly_report_{mandate_id}.json. Returns path."""
    gen = WeeklyReportGenerator()
    report = gen.generate(
        mandate,
        benchmark_result,
        key_trades=key_trades or [],
        risk_events=risk_events or [],
        no_trade_days=no_trade_days,
        no_trade_reasons=no_trade_reasons or [],
        daily_research=daily_research or [],
    )
    report_dir = report_dir or Path(".")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"weekly_report_{mandate.mandate_id}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(gen.to_dict(report), f, ensure_ascii=False, indent=2)
    return str(report_path)
