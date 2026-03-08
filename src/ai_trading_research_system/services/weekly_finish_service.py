"""
Finish week: benchmark + report + summary. Used by weekly_paper_pipe after execution loop only.
Pipe does: mandate, snapshot, research, allocation, execution; this service does the rest.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.services.benchmark_service import get_benchmark_return, compare_to_benchmark
from ai_trading_research_system.services.report_service import (
    generate_and_write as report_generate_and_write,
    build_weekly_result_summary,
)

# Avoid circular import: pipe defines WeeklyPaperResult
def _result_type():
    from ai_trading_research_system.pipeline.weekly_paper_pipe import WeeklyPaperResult
    return WeeklyPaperResult


def finish_week(
    *,
    mandate: WeeklyTradingMandate,
    capital: float,
    benchmark: str,
    duration_days: int,
    total_pnl: float,
    total_trades: int,
    run_ids: list[int],
    key_trades: list[str],
    no_trade_reasons: list[str],
    daily_research: list[dict[str, Any]],
    snapshot_source: str,
    use_mock: bool,
    state: str,
    report_dir: Path,
) -> Any:
    """
    After execution loop: compute benchmark, write report, build summary, return WeeklyPaperResult.
    Pipe must only do mandate, snapshot, research, allocation, execution; then call this.
    """
    WeeklyPaperResult = _result_type()
    portfolio_return = total_pnl / capital if capital else 0.0
    benchmark_return, benchmark_source = get_benchmark_return(
        symbol=benchmark,
        lookback_days=duration_days,
    )
    if use_mock:
        benchmark_source = "mock"
    bench_result = compare_to_benchmark(
        portfolio_return=portfolio_return,
        benchmark_return=benchmark_return,
        max_drawdown=0.0,
        trade_count=total_trades,
        period=f"day_0_to_{duration_days}",
        benchmark_source=benchmark_source,
    )
    report_dir = report_dir or Path(".")
    report_path = report_generate_and_write(
        mandate,
        bench_result,
        key_trades=key_trades,
        risk_events=[],
        no_trade_days=len(no_trade_reasons),
        no_trade_reasons=no_trade_reasons[:5],
        daily_research=daily_research,
        report_dir=report_dir,
    )
    market_data_source = "mock" if use_mock else "yfinance"
    summary = build_weekly_result_summary(
        portfolio_return=portfolio_return,
        benchmark_return=benchmark_return,
        excess_return=bench_result.excess_return,
        total_trades=total_trades,
        total_pnl=total_pnl,
        report_path=report_path,
        daily_research_count=len(daily_research),
        snapshot_source=snapshot_source,
        market_data_source=market_data_source,
        benchmark_source=benchmark_source,
    )
    return WeeklyPaperResult(
        ok=True,
        mandate_id=mandate.mandate_id,
        status=state,
        capital_limit=capital,
        benchmark=benchmark,
        engine_type="nautilus",
        used_nautilus=True,
        report_path=report_path,
        summary=summary,
        strategy_run_ids=run_ids,
    )
