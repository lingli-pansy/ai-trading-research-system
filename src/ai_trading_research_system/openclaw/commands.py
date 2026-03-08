"""
OpenClaw commands: map skill names to application.commands.
Each skill invokes exactly one command; no business logic here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_trading_research_system.application.commands import (
    run_research_symbol,
    run_backtest_symbol,
    run_demo,
    run_weekly_autonomous_paper,
    generate_weekly_report,
)
from ai_trading_research_system.autonomous.schemas import WeeklyTradingMandate
from ai_trading_research_system.autonomous.benchmark import BenchmarkResult


def research_symbol(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> Any:
    """Skill: research_symbol → application.commands.run_research_symbol."""
    return run_research_symbol(symbol, use_mock=use_mock, use_llm=use_llm)


def backtest_symbol(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> Any:
    """Skill: backtest_symbol → application.commands.run_backtest_symbol."""
    return run_backtest_symbol(
        symbol,
        start_date=start_date,
        end_date=end_date,
        use_mock=use_mock,
        use_llm=use_llm,
    )


def run_demo_command(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> Any:
    """Skill: run_demo → application.commands.run_demo."""
    return run_demo(symbol, use_mock=use_mock, use_llm=use_llm)


def weekly_autonomous_paper(
    *,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    duration_days: int = 5,
    auto_confirm: bool = True,
    use_mock: bool = False,
    use_llm: bool = False,
    report_dir: Path | None = None,
) -> Any:
    """Skill: weekly_autonomous_paper → application.commands.run_weekly_autonomous_paper."""
    return run_weekly_autonomous_paper(
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        auto_confirm=auto_confirm,
        use_mock=use_mock,
        use_llm=use_llm,
        report_dir=report_dir,
    )


def weekly_report(
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
    """Skill: weekly_report → application.commands.generate_weekly_report."""
    return generate_weekly_report(
        mandate,
        benchmark_result,
        key_trades=key_trades,
        risk_events=risk_events,
        no_trade_days=no_trade_days,
        no_trade_reasons=no_trade_reasons,
        daily_research=daily_research,
        report_dir=report_dir,
    )
