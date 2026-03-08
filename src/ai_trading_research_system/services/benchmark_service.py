"""
Benchmark service: fetch benchmark return for period and compare portfolio vs benchmark.
Used by UC-09 weekly controller and by application.commands when generating reports.
"""
from __future__ import annotations

from ai_trading_research_system.autonomous.benchmark import (
    get_benchmark_return_for_period,
    BenchmarkComparator,
    BenchmarkResult,
)


def get_benchmark_return(
    symbol: str = "SPY",
    start_date: str | None = None,
    end_date: str | None = None,
    lookback_days: int = 5,
) -> tuple[float, str]:
    """Return (benchmark_return_decimal, source). Source is 'yfinance' or 'mock'."""
    return get_benchmark_return_for_period(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        lookback_days=lookback_days,
    )


def compare_to_benchmark(
    portfolio_return: float,
    benchmark_return: float,
    max_drawdown: float = 0.0,
    trade_count: int = 0,
    period: str = "",
    benchmark_source: str = "mock",
) -> BenchmarkResult:
    """Compare portfolio vs benchmark; return BenchmarkResult."""
    comp = BenchmarkComparator()
    return comp.compare(
        portfolio_return=portfolio_return,
        benchmark_return=benchmark_return,
        max_drawdown=max_drawdown,
        trade_count=trade_count,
        period=period or "week",
        benchmark_source=benchmark_source,
    )
