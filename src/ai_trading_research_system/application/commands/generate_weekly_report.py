"""Command: generate weekly report. Calls report service only."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult
from ai_trading_research_system.services.report_service import generate_and_write


def generate_weekly_report(
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
    """Generate weekly report JSON via report_service; returns path to written file."""
    return generate_and_write(
        mandate,
        benchmark_result,
        key_trades=key_trades,
        risk_events=risk_events,
        no_trade_days=no_trade_days,
        no_trade_reasons=no_trade_reasons,
        daily_research=daily_research,
        report_dir=report_dir,
    )
