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
    turnover_pct: float = 0.0,
    opportunity_ranking: list[dict[str, Any]] | None = None,
    replacement_decisions: list[dict[str, Any]] | None = None,
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
        turnover_pct=turnover_pct,
        opportunity_ranking=opportunity_ranking or [],
        replacement_decisions=replacement_decisions or [],
    )
    report_dir = report_dir or Path(".")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"weekly_report_{mandate.mandate_id}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(gen.to_dict(report), f, ensure_ascii=False, indent=2)
    return str(report_path)


def build_weekly_result_summary(
    *,
    portfolio_return: float,
    benchmark_return: float,
    excess_return: float,
    total_trades: int,
    total_pnl: float,
    report_path: str,
    daily_research_count: int,
    snapshot_source: str,
    market_data_source: str,
    benchmark_source: str,
) -> dict[str, Any]:
    """Build the summary dict for WeeklyPaperResult. Used by weekly_paper_pipe only for result assembly."""
    return {
        "portfolio_return": portfolio_return,
        "benchmark_return": benchmark_return,
        "excess_return": excess_return,
        "trade_count": total_trades,
        "pnl": total_pnl,
        "report_path": report_path,
        "daily_research_count": daily_research_count,
        "analysis_in_report": True,
        "snapshot_source": snapshot_source,
        "market_data_source": market_data_source,
        "benchmark_source": benchmark_source,
    }
