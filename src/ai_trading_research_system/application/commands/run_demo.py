"""Command: run demo (research → strategy → backtest → store). Calls backtest pipeline only."""
from __future__ import annotations

from ai_trading_research_system.pipeline.backtest_pipe import run as run_backtest_pipe
from ai_trading_research_system.pipeline.backtest_pipe import BacktestPipeResult


def run_demo(
    symbol: str,
    *,
    use_mock: bool = False,
    use_llm: bool = False,
) -> BacktestPipeResult:
    """Run E2E demo: research → strategy → backtest → store. Returns BacktestPipeResult (CLI formats 4 blocks)."""
    return run_backtest_pipe(
        symbol=symbol,
        start_date=None,
        end_date=None,
        use_mock=use_mock,
        use_llm=use_llm,
    )
