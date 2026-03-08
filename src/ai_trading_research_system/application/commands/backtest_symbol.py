"""Command: backtest symbol. Calls backtest pipeline only."""
from __future__ import annotations

from ai_trading_research_system.pipeline.backtest_pipe import run as run_backtest_pipe
from ai_trading_research_system.pipeline.backtest_pipe import BacktestPipeResult


def run_backtest_symbol(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> BacktestPipeResult:
    """Run research → backtest → store; returns BacktestPipeResult."""
    return run_backtest_pipe(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        use_mock=use_mock,
        use_llm=use_llm,
    )
