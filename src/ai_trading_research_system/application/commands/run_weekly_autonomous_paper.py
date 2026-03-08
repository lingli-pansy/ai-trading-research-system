"""Command: run UC-09 weekly autonomous paper. Calls weekly_paper_pipe only."""
from __future__ import annotations

from pathlib import Path

from ai_trading_research_system.pipeline.weekly_paper_pipe import (
    run_weekly_autonomous_paper as _run_pipe,
    WeeklyPaperResult,
)


def run_weekly_autonomous_paper(
    *,
    capital: float = 10_000.0,
    benchmark: str = "SPY",
    duration_days: int = 5,
    auto_confirm: bool = True,
    use_mock: bool = False,
    use_llm: bool = False,
    report_dir: Path | None = None,
    symbols: list[str] | None = None,
) -> WeeklyPaperResult:
    """Run weekly autonomous paper pipeline; symbols = watchlist/universe，空则默认单 symbol。"""
    return _run_pipe(
        capital=capital,
        benchmark=benchmark,
        duration_days=duration_days,
        auto_confirm=auto_confirm,
        use_mock=use_mock,
        use_llm=use_llm,
        report_dir=report_dir,
        symbols=symbols,
    )
